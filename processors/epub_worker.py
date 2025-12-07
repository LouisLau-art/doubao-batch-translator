#!/usr/bin/env python3
"""
ePub 电子书翻译处理器 (增强版)
修复 container.xml 命名空间解析问题，支持中断保存
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
    
    # 命名空间定义 (仅作参考，解析时尽量使用忽略命名空间的策略)
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
                                # 进度条范围 0.25 -> 0.95
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
                logger.warning("\n⚠️ 任务被取消！正在保存已完成的进度...")
                self._repack_epub(temp_dir, output_path)
                logger.info(f"✅ 半成品已保存至: {output_path}")
                raise

            except KeyboardInterrupt:
                logger.warning("\n⚠️ 检测到用户中断 (Ctrl+C)！正在抢救已翻译的内容...")
                self._repack_epub(temp_dir, output_path)
                logger.info(f"✅ 半成品已保存至: {output_path}")
                raise

            except Exception as e:
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
            logger.warning("警告: 未找到 mimetype 文件，此 ePub 可能不标准")
    
    def _parse_opf(self, epub_dir: str) -> EpubInfo:
        """
        解析 OPF 文件 (增强鲁棒性版本)
        不再依赖严格的 namespace 匹配，而是搜索标签名
        """
        container_path = os.path.join(epub_dir, 'META-INF', 'container.xml')
        try:
            tree = ET.parse(container_path)
            root = tree.getroot()
            
            # [关键修复] 暴力搜索 rootfile 标签，忽略命名空间
            rootfile_elem = None
            for elem in root.iter():
                # ElementTree 的 tag 通常是 {namespace}tagname
                if elem.tag.endswith('rootfile'):
                    rootfile_elem = elem
                    break
            
            if rootfile_elem is None:
                # 打印出所有 tag 方便调试
                tags = [e.tag for e in root.iter()]
                raise ValueError(f"无法在 container.xml 中找到 rootfile。解析到的元素: {tags}")
                
            opf_rel_path = rootfile_elem.get('full-path')
            if not opf_rel_path:
                raise ValueError("rootfile 标签缺少 full-path 属性")
                
            opf_path = os.path.join(epub_dir, opf_rel_path)
            opf_dir = os.path.dirname(opf_path)
            
        except Exception as e:
            raise Exception(f"解析 container.xml 失败: {e}")

        # 解析 OPF
        if not os.path.exists(opf_path):
             raise FileNotFoundError(f"找不到 OPF 文件: {opf_path}")

        opf_tree = ET.parse(opf_path)
        opf_root = opf_tree.getroot()
        
        # 不再使用严格的 namespace map
        # root_tag = opf_root.tag
        # ns_url = root_tag.split('}')[0].strip('{') if '}' in root_tag else ''
        # ns_map = {'opf': ns_url} if ns_url else {}
        
        content_files = []
        toc_file = None
        toc_type = ""
        
        # 同样使用迭代搜索，兼容性更强
        # 查找 manifest 下的所有 item
        for elem in opf_root.iter():
            if elem.tag.endswith('item'):
                media_type = elem.get('media-type', '')
                href = elem.get('href', '')
                properties = elem.get('properties', '')
                
                if not href: continue
                
                full_path = os.path.join(opf_dir, href)
                
                # 识别 HTML/XHTML 文本
                if 'html' in media_type.lower() or 'xhtml' in media_type.lower():
                    content_files.append(full_path)
                
                # 识别目录
                if properties == 'nav' or 'ncx' in media_type:
                    toc_file = full_path
                    toc_type = 'nav' if properties == 'nav' else 'ncx'
                
        metadata = self._extract_metadata(opf_root)
        return EpubInfo(opf_path, opf_dir, content_files, toc_file, toc_type, metadata)
    
    def _extract_metadata(self, opf_root) -> Dict[str, str]:
        """提取元数据 (忽略命名空间前缀)"""
        metadata = {}
        for elem in opf_root.iter():
            tag = elem.tag.lower()
            if tag.endswith('title'):
                metadata['title'] = elem.text.strip() if elem.text else ""
            elif tag.endswith('creator'):
                metadata['creator'] = elem.text.strip() if elem.text else ""
            elif tag.endswith('description'):
                metadata['description'] = elem.text.strip() if elem.text else ""
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
            
            # 回写需要重新 parse
            tree = ET.parse(epub_info.opf_path)
            root = tree.getroot()
            
            # 使用简单的迭代查找来回写，不依赖 namespace
            result_map = dict(zip(keys, results))
            
            for elem in root.iter():
                for key in list(result_map.keys()):
                    # 匹配标签名后缀 (如 dc:title 或 title)
                    if elem.tag.lower().endswith(key) and result_map[key] != "[TRANSLATION_FAILED]":
                        # 简单的防误判：只有当原文内容匹配时才替换（防止多个 creator 的情况搞混，暂简化处理）
                        if elem.text and elem.text.strip() == epub_info.metadata[key]:
                            elem.text = result_map[key]
                            logger.info(f"元数据 {key} 已翻译")
            
            # 注册常用命名空间，防止输出时乱码 (虽然解析时不依赖，但写入时最好加上)
            ET.register_namespace('dc', "http://purl.org/dc/elements/1.1/")
            ET.register_namespace('opf', "http://www.idpf.org/2007/opf")
                
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
            
            # 查找所有 navLabel 下的 text，忽略命名空间
            text_elems = []
            texts = []
            
            for elem in root.iter():
                if elem.tag.endswith('text') and elem.text and elem.text.strip():
                    text_elems.append(elem)
                    texts.append(elem.text.strip())
            
            if texts:
                translated = await self.translator.translate_batch(texts, source_lang, target_lang)
                for elem, trans_text in zip(text_elems, translated):
                    if trans_text and trans_text != "[TRANSLATION_FAILED]":
                        elem.text = trans_text
                            
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