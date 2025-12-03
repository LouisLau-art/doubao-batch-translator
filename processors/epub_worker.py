#!/usr/bin/env python3
"""
ePub 电子书翻译处理器 (高性能并发版)
支持解压、解析、翻译元数据、目录和内容，最后重新打包成标准 ePub
"""

import zipfile
import tempfile
import os
import logging
import asyncio  # 新增
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from xml.etree import ElementTree as ET
from dataclasses import dataclass

from .html_worker import HTMLProcessor

logger = logging.getLogger(__name__)


@dataclass
class EpubInfo:
    """ePub 文件信息"""
    opf_path: str
    opf_dir: str
    content_files: List[str]
    toc_file: Optional[str] = None
    toc_type: str = ""  # "ncx" or "nav"
    metadata: Dict[str, str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EpubProcessor:
    """ePub 电子书翻译处理器"""
    
    # ePub 规范命名空间
    CONTAINER_NS = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
    OPF_NS = {'opf': 'http://www.idpf.org/2007/opf'}
    DC_NS = 'http://purl.org/dc/elements/1.1/'
    NCX_NS = 'http://www.daisy.org/z3986/2005/ncx/'
    
    def __init__(self, translator):
        """初始化 ePub 处理器"""
        self.translator = translator
        self.html_processor = HTMLProcessor(translator)
        # 限制同时处理的文件数，防止打开过多文件句柄导致 OS 报错
        # 注意：这不同于 API 的并发限制，这是文件系统的限制
        self.file_semaphore = asyncio.Semaphore(50) 
    
    async def translate_epub(
        self, 
        input_path: str, 
        output_path: str,
        source_lang: Optional[str] = None,
        target_lang: str = "zh",
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """翻译 ePub 文件"""
        logger.info(f"开始翻译 ePub 文件: {input_path}")
        
        if progress_callback:
            progress_callback(0.0, "准备处理...")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 解压 ePub 文件
                if progress_callback: progress_callback(0.05, "解压 ePub 文件...")
                self._extract_epub(input_path, temp_dir)
                
                # 2. 解析 OPF 文件和内容
                if progress_callback: progress_callback(0.1, "解析 ePub 结构...")
                epub_info = self._parse_opf(temp_dir)
                logger.info(f"发现 {len(epub_info.content_files)} 个内容文件")
                
                # 3. 翻译元数据 (并发执行)
                if progress_callback: progress_callback(0.15, "翻译书籍元数据...")
                await self._translate_metadata(epub_info, source_lang, target_lang)
                
                # 4. 翻译目录 (并发执行)
                if epub_info.toc_file:
                    if progress_callback: progress_callback(0.2, "翻译目录...")
                    await self._translate_toc(epub_info, source_lang, target_lang)
                
                # 5. 翻译内容文件 (核心改进：完全并发!)
                total_files = len(epub_info.content_files)
                completed_files = 0
                stats = {'success': 0, 'failed': 0}
                
                # 定义单个文件处理任务
                async def process_single_file(file_path):
                    nonlocal completed_files
                    async with self.file_semaphore: # 限制文件并发数
                        try:
                            await self.html_processor.process_file(
                                input_file=file_path,
                                output_file=file_path,  # 原地覆盖
                                source_lang=source_lang,
                                target_lang=target_lang
                            )
                            stats['success'] += 1
                        except Exception as e:
                            logger.warning(f"翻译文件失败 {os.path.basename(file_path)}: {e}")
                            stats['failed'] += 1
                        finally:
                            completed_files += 1
                            if progress_callback:
                                # 进度范围 0.25 -> 0.95
                                current_progress = 0.25 + (0.7 * (completed_files / total_files))
                                progress_callback(current_progress, f"翻译进度 {completed_files}/{total_files}")

                # 创建所有任务并并发执行
                tasks = [process_single_file(f) for f in epub_info.content_files]
                await asyncio.gather(*tasks)
                
                # 6. 重新打包
                if progress_callback: progress_callback(0.98, "重新打包 ePub...")
                self._repack_epub(temp_dir, output_path)
                
                if progress_callback: progress_callback(1.0, "完成!")
                
                return {
                    'success': True,
                    'total_files': total_files,
                    'success_count': stats['success'],
                    'failed_count': stats['failed'],
                    'output_file': output_path
                }
                
        except Exception as e:
            logger.error(f"翻译 ePub 失败: {e}", exc_info=True)
            raise
    
    def _extract_epub(self, epub_path: str, dest_dir: str):
        """解压 ePub 文件"""
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        # 简单验证
        if not os.path.exists(os.path.join(dest_dir, 'mimetype')):
            logger.warning("警告: 未找到 mimetype 文件，可能是不标准的 ePub")
    
    def _parse_opf(self, epub_dir: str) -> EpubInfo:
        """解析 OPF 文件结构"""
        # 1. 读取 container.xml
        container_path = os.path.join(epub_dir, 'META-INF', 'container.xml')
        try:
            tree = ET.parse(container_path)
            root = tree.getroot()
            # 处理可能的默认命名空间
            ns = {'ns': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = root.find('.//ns:rootfile', ns)
            if rootfile is None:
                # 尝试不带命名空间查找
                rootfile = root.find('.//rootfile')
            
            if rootfile is None:
                raise ValueError("无法在 container.xml 中找到 rootfile")
                
            opf_rel_path = rootfile.get('full-path')
            opf_path = os.path.join(epub_dir, opf_rel_path)
            opf_dir = os.path.dirname(opf_path)
            
        except Exception as e:
            raise Exception(f"解析 container.xml 失败: {e}")

        # 2. 解析 OPF
        opf_tree = ET.parse(opf_path)
        opf_root = opf_tree.getroot()
        
        # 命名空间处理（处理某些不规范的 OPF）
        # 获取根元素的命名空间，例如 {http://www.idpf.org/2007/opf}package
        root_tag = opf_root.tag
        ns_url = root_tag.split('}')[0].strip('{') if '}' in root_tag else ''
        ns_map = {'opf': ns_url} if ns_url else {}
        
        content_files = []
        toc_file = None
        toc_type = ""
        
        # 查找 manifest items
        # 如果有命名空间则用命名空间，否则直接查 tag
        items = opf_root.findall('.//opf:item', ns_map) if ns_url else opf_root.findall('.//item')
        
        for item in items:
            media_type = item.get('media-type', '')
            href = item.get('href', '')
            properties = item.get('properties', '')
            
            if not href: continue
            
            # 识别文本内容
            if 'html' in media_type.lower() or 'xhtml' in media_type.lower():
                full_path = os.path.join(opf_dir, href)
                content_files.append(full_path)
            
            # 识别目录
            if properties == 'nav' or 'ncx' in media_type:
                full_path = os.path.join(opf_dir, href)
                toc_file = full_path
                toc_type = 'nav' if properties == 'nav' else 'ncx'
                
        # 提取元数据 (简化版，复用现有逻辑)
        metadata = self._extract_metadata(opf_root, ns_map)
        
        return EpubInfo(opf_path, opf_dir, content_files, toc_file, toc_type, metadata)
    
    def _extract_metadata(self, opf_root, ns_map) -> Dict[str, str]:
        """提取元数据"""
        metadata = {}
        # 定义 DC 命名空间
        dc_ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
        
        for key in ['title', 'creator', 'description']:
            elem = opf_root.find(f'.//dc:{key}', dc_ns)
            if elem is not None and elem.text:
                metadata[key] = elem.text.strip()
        return metadata
    
    async def _translate_metadata(self, epub_info: EpubInfo, source_lang: str, target_lang: str):
        """翻译元数据"""
        if not epub_info.metadata: return
        
        # 准备翻译任务
        texts_to_trans = []
        keys = []
        for k, v in epub_info.metadata.items():
            if v:
                texts_to_trans.append(v)
                keys.append(k)
        
        if not texts_to_trans: return
        
        try:
            # 批量翻译
            results = await self.translator.translate_batch(texts_to_trans, source_lang, target_lang)
            
            # 更新 XML
            # 注意：这里需要重新 parse 并保存
            tree = ET.parse(epub_info.opf_path)
            root = tree.getroot()
            dc_ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
            
            for k, translated_text in zip(keys, results):
                if translated_text and translated_text != "[TRANSLATION_FAILED]":
                    elem = root.find(f'.//dc:{k}', dc_ns)
                    if elem is not None:
                        elem.text = translated_text
                        logger.info(f"元数据 {k} 已翻译")
            
            # 注册命名空间以防保存时前缀混乱
            ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/")
            if 'opf' in self.OPF_NS:
                ET.register_namespace('', "http://www.idpf.org/2007/opf")
                
            tree.write(epub_info.opf_path, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            logger.warning(f"元数据翻译失败: {e}")

    async def _translate_toc(self, epub_info: EpubInfo, source_lang: str, target_lang: str):
        """翻译目录"""
        if epub_info.toc_type == 'ncx':
            await self._translate_ncx(epub_info.toc_file, source_lang, target_lang)
        elif epub_info.toc_type == 'nav':
            # nav 本质是 HTML，直接复用 HTMLProcessor
            await self.html_processor.process_file(
                epub_info.toc_file, epub_info.toc_file, source_lang, target_lang
            )

    async def _translate_ncx(self, ncx_path: str, source_lang: str, target_lang: str):
        """翻译 NCX 目录"""
        try:
            tree = ET.parse(ncx_path)
            root = tree.getroot()
            ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
            
            # 查找所有 navLabel/text
            text_elems = root.findall('.//ncx:text', ns)
            texts = [e.text for e in text_elems if e.text and e.text.strip()]
            
            if texts:
                translated = await self.translator.translate_batch(texts, source_lang, target_lang)
                
                # 回填
                idx = 0
                for e in text_elems:
                    if e.text and e.text.strip():
                        if idx < len(translated):
                            e.text = translated[idx]
                            idx += 1
                            
                tree.write(ncx_path, encoding='utf-8', xml_declaration=True)
                logger.info(f"NCX 目录翻译完成，共 {len(texts)} 项")
                
        except Exception as e:
            logger.warning(f"NCX 目录翻译失败: {e}")

    def _repack_epub(self, source_dir: str, output_path: str):
        """标准打包流程"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. 写入 mimetype (无压缩)
            mimetype_path = os.path.join(source_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            # 2. 写入其他文件
            for root, _, files in os.walk(source_dir):
                for f in files:
                    if f == 'mimetype': continue
                    full_path = os.path.join(root, f)
                    arc_name = os.path.relpath(full_path, source_dir)
                    zf.write(full_path, arc_name)