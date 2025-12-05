#!/usr/bin/env python3
"""
ePub 电子书翻译处理器 (支持中断保存版)
"""

import zipfile
import tempfile
import os
import logging
import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
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
    toc_type: str = ""
    metadata: Dict[str, str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EpubProcessor:
    """ePub 电子书翻译处理器"""
    
    CONTAINER_NS = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
    OPF_NS = {'opf': 'http://www.idpf.org/2007/opf'}
    DC_NS = 'http://purl.org/dc/elements/1.1/'
    
    def __init__(self, translator):
        self.translator = translator
        self.html_processor = HTMLProcessor(translator)
        # 限制文件并发数，防止打开过多文件句柄
        self.file_semaphore = asyncio.Semaphore(50) 
    
    async def translate_epub(
        self, 
        input_path: str, 
        output_path: str,
        source_lang: Optional[str] = None,
        target_lang: str = "zh",
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """翻译 ePub 文件 (支持中断保存)"""
        logger.info(f"开始翻译 ePub 文件: {input_path}")
        
        if progress_callback:
            progress_callback(0.0, "准备处理...")
        
        # 使用临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. 解压
                if progress_callback: progress_callback(0.05, "解压 ePub 文件...")
                self._extract_epub(input_path, temp_dir)
                
                # 2. 解析
                if progress_callback: progress_callback(0.1, "解析 ePub 结构...")
                epub_info = self._parse_opf(temp_dir)
                logger.info(f"发现 {len(epub_info.content_files)} 个内容文件")
                
                # 3. 翻译元数据
                if progress_callback: progress_callback(0.15, "翻译书籍元数据...")
                await self._translate_metadata(epub_info, source_lang, target_lang)
                
                # 4. 翻译目录
                if epub_info.toc_file:
                    if progress_callback: progress_callback(0.2, "翻译目录...")
                    await self._translate_toc(epub_info, source_lang, target_lang)
                
                # 5. 翻译内容文件 (核心循环)
                total_files = len(epub_info.content_files)
                completed_files = 0
                stats = {'success': 0, 'failed': 0}
                
                async def process_single_file(file_path):
                    nonlocal completed_files
                    async with self.file_semaphore:
                        try:
                            await self.html_processor.process_file(
                                input_file=file_path,
                                output_file=file_path,
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
                                current_progress = 0.25 + (0.7 * (completed_files / total_files))
                                progress_callback(current_progress, f"翻译进度 {completed_files}/{total_files}")

                tasks = [process_single_file(f) for f in epub_info.content_files]
                
                # 等待所有任务完成
                await asyncio.gather(*tasks)
                
                # 6. 正常打包
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

            except asyncio.CancelledError:
                # 处理异步取消（Ctrl+C在某些环境下会触发这个）
                logger.warning("\n⚠️ 任务被取消！正在保存已完成的进度...")
                self._repack_epub(temp_dir, output_path)
                logger.info(f"✅ 半成品已保存至: {output_path}")
                raise

            except KeyboardInterrupt:
                # [关键修复] 捕获 Ctrl+C
                logger.warning("\n⚠️ 检测到用户中断 (Ctrl+C)！正在抢救已翻译的内容...")
                self._repack_epub(temp_dir, output_path)
                logger.info(f"✅ 半成品已保存至: {output_path}")
                # 重新抛出异常，让主程序正常退出
                raise

            except Exception as e:
                # 发生其他严重错误时，也尝试保存
                logger.error(f"发生错误: {e}，尝试保存现有进度...")
                try:
                    self._repack_epub(temp_dir, output_path)
                    logger.info(f"✅ 现有进度已保存至: {output_path}")
                except:
                    pass
                raise e
    
    def _extract_epub(self, epub_path: str, dest_dir: str):
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        if not os.path.exists(os.path.join(dest_dir, 'mimetype')):
            logger.warning("警告: 未找到 mimetype 文件")
    
    def _parse_opf(self, epub_dir: str) -> EpubInfo:
        container_path = os.path.join(epub_dir, 'META-INF', 'container.xml')
        try:
            tree = ET.parse(container_path)
            root = tree.getroot()
            ns = {'ns': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = root.find('.//ns:rootfile', ns) or root.find('.//rootfile')
            
            if rootfile is None:
                raise ValueError("无法在 container.xml 中找到 rootfile")
                
            opf_rel_path = rootfile.get('full-path')
            opf_path = os.path.join(epub_dir, opf_rel_path)
            opf_dir = os.path.dirname(opf_path)
            
        except Exception as e:
            raise Exception(f"解析 container.xml 失败: {e}")

        opf_tree = ET.parse(opf_path)
        opf_root = opf_tree.getroot()
        
        root_tag = opf_root.tag
        ns_url = root_tag.split('}')[0].strip('{') if '}' in root_tag else ''
        ns_map = {'opf': ns_url} if ns_url else {}
        
        content_files = []
        toc_file = None
        toc_type = ""
        
        items = opf_root.findall('.//opf:item', ns_map) if ns_url else opf_root.findall('.//item')
        
        for item in items:
            media_type = item.get('media-type', '')
            href = item.get('href', '')
            properties = item.get('properties', '')
            
            if not href: continue
            
            full_path = os.path.join(opf_dir, href)
            
            # 识别文本
            if 'html' in media_type.lower() or 'xhtml' in media_type.lower():
                content_files.append(full_path)
            
            # 识别目录
            if properties == 'nav' or 'ncx' in media_type:
                toc_file = full_path
                toc_type = 'nav' if properties == 'nav' else 'ncx'
                
        metadata = self._extract_metadata(opf_root, ns_map)
        return EpubInfo(opf_path, opf_dir, content_files, toc_file, toc_type, metadata)
    
    def _extract_metadata(self, opf_root, ns_map) -> Dict[str, str]:
        metadata = {}
        dc_ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
        for key in ['title', 'creator', 'description']:
            elem = opf_root.find(f'.//dc:{key}', dc_ns)
            if elem is not None and elem.text:
                metadata[key] = elem.text.strip()
        return metadata
    
    async def _translate_metadata(self, epub_info: EpubInfo, source_lang: str, target_lang: str):
        if not epub_info.metadata: return
        
        texts_to_trans = []
        keys = []
        for k, v in epub_info.metadata.items():
            if v:
                texts_to_trans.append(v)
                keys.append(k)
        
        if not texts_to_trans: return
        
        try:
            results = await self.translator.translate_batch(texts_to_trans, source_lang, target_lang)
            
            tree = ET.parse(epub_info.opf_path)
            root = tree.getroot()
            dc_ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
            
            for k, translated_text in zip(keys, results):
                if translated_text and translated_text != "[TRANSLATION_FAILED]":
                    elem = root.find(f'.//dc:{k}', dc_ns)
                    if elem is not None:
                        elem.text = translated_text
                        logger.info(f"元数据 {k} 已翻译")
            
            ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/")
            if 'opf' in self.OPF_NS:
                ET.register_namespace('', "http://www.idpf.org/2007/opf")
                
            tree.write(epub_info.opf_path, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            logger.warning(f"元数据翻译失败: {e}")

    async def _translate_toc(self, epub_info: EpubInfo, source_lang: str, target_lang: str):
        if epub_info.toc_type == 'ncx':
            await self._translate_ncx(epub_info.toc_file, source_lang, target_lang)
        elif epub_info.toc_type == 'nav':
            await self.html_processor.process_file(
                epub_info.toc_file, epub_info.toc_file, source_lang, target_lang
            )

    async def _translate_ncx(self, ncx_path: str, source_lang: str, target_lang: str):
        try:
            tree = ET.parse(ncx_path)
            root = tree.getroot()
            ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
            
            text_elems = root.findall('.//ncx:text', ns)
            texts = [e.text for e in text_elems if e.text and e.text.strip()]
            
            if texts:
                translated = await self.translator.translate_batch(texts, source_lang, target_lang)
                idx = 0
                for e in text_elems:
                    if e.text and e.text.strip() and idx < len(translated):
                        e.text = translated[idx]
                        idx += 1
                            
                tree.write(ncx_path, encoding='utf-8', xml_declaration=True)
                logger.info(f"NCX 目录翻译完成")
        except Exception as e:
            logger.warning(f"NCX 目录翻译失败: {e}")

    def _repack_epub(self, source_dir: str, output_path: str):
        """重新打包 ePub"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            mimetype_path = os.path.join(source_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            for root, _, files in os.walk(source_dir):
                for f in files:
                    if f == 'mimetype': continue
                    full_path = os.path.join(root, f)
                    arc_name = os.path.relpath(full_path, source_dir)
                    zf.write(full_path, arc_name)