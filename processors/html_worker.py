#!/usr/bin/env python3
"""
HTML处理器 - 基于现有TypeScript逻辑重构
智能识别URL、代码块等不翻译内容，专注于HTML文本翻译
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Comment

from core import AsyncTranslator, ValidationError
from core.token_tracker import TokenTracker
from core.exceptions import FileProcessingError


logger = logging.getLogger(__name__)


class HTMLProcessor:
    """HTML文件翻译处理器"""
    
    def __init__(self, translator: AsyncTranslator):
        """初始化HTML处理器
        
        Args:
            translator: 异步翻译器实例
        """
        self.translator = translator
        self.token_tracker = TokenTracker()  # 用于token估算
        
        # 模型限制 - 设置为800以留出足够误差余地
        self.MAX_TOKEN_PER_TEXT = 800  # 最大输入Token长度
        
        # 不翻译的标签列表
        self.exclude_tags = {
            'script', 'style', 'code', 'pre', 'textarea', 'noscript',
            'meta', 'link', 'title', 'head'
        }
        
        # 不翻译的属性列表
        self.exclude_attributes = {
            'id', 'class', 'href', 'src', 'alt', 'title', 'aria-label',
            'data-*', 'style'
        }
        
        # URL匹配模式
        self.url_pattern = re.compile(
            r'^(https?://|ftp://|file://|mailto:|tel:|#|/|\.\./|\./|javascript:)',
            re.IGNORECASE
        )
        
        # 代码块匹配模式
        self.code_patterns = [
            r'<code[^>]*>.*?</code>',
            r'<pre[^>]*>.*?</pre>',
            r'`[^`]+`',
            r'```[\s\S]*?```'
        ]
    
    def _is_url(self, text: str) -> bool:
        """判断文本是否为URL
        
        Args:
            text: 待检查文本
            
        Returns:
            是否为URL
        """
        text = text.strip()
        
        # 检查是否包含URL模式
        if self.url_pattern.match(text):
            return True
        
        # 检查是否为常见域名格式 (如 example.com, www.example.org)
        # 只有当文本看起来像域名时才返回 True
        try:
            parsed = urlparse(text)
            # 只有当有明确的 scheme 时才认为是 URL
            if parsed.scheme and parsed.scheme in ('http', 'https', 'ftp', 'file', 'mailto', 'tel'):
                return True
            
            # 检查是否为纯域名格式 (无空格，包含点，且看起来像域名)
            if ' ' not in text and '.' in text:
                # 检查是否匹配常见域名模式 (如 example.com, www.test.org)
                domain_pattern = re.compile(
                    r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)+$'
                )
                return bool(domain_pattern.match(text))
            
            return False
        except:
            return False
    
    def _is_code_like(self, text: str) -> bool:
        """判断文本是否像代码
        
        Args:
            text: 待检查文本
            
        Returns:
            是否像代码
        """
        text = text.strip()
        
        # 检查代码块模式
        for pattern in self.code_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True
        
        # 检查是否包含编程语言特征
        code_indicators = [
            'function', 'var ', 'const ', 'let ', 'class ', 'import ',
            'from ', 'def ', 'if __name__', 'console.log', 'print(',
            'System.out.println', 'printf', 'cout <<', '#include',
            '<?php', '<%', '{{{', '{{{!'
        ]
        
        return any(indicator in text for indicator in code_indicators)
    
    def _extract_text_nodes(self, element) -> List[Tuple[NavigableString, str]]:
        """提取可翻译的文本节点
        
        Args:
            element: BeautifulSoup元素
            
        Returns:
            文本节点和父元素标签的元组列表
        """
        results = []
        
        for content in element.descendants:
            if isinstance(content, NavigableString):
                text = content.string
                if text and text.strip():
                    # 检查是否应该翻译
                    if self._should_translate_element(content.parent):
                        results.append((content, content.parent.name))
            
            elif isinstance(content, Comment):
                # 跳过HTML注释
                continue
        
        return results
    
    def _should_translate_element(self, element) -> bool:
        """判断元素是否应该翻译
        
        Args:
            element: BeautifulSoup元素
            
        Returns:
            是否应该翻译
        """
        if not element.name:
            return True
        
        # 检查标签是否在排除列表中
        if element.name.lower() in self.exclude_tags:
            return False
        
        # 检查是否有特定的属性标识
        special_classes = ['no-translate', 'translation-exclude', 'skip-translation']
        if any(cls in element.get('class', []) for cls in special_classes):
            return False
        
        # 检查是否有数据属性标识
        if element.get('data-no-translate') or element.get('data-skip-translate'):
            return False
        
        return True
    
    def _extract_translatable_attributes(self, element) -> List[Tuple[str, str]]:
        """提取可翻译的属性
        
        Args:
            element: BeautifulSoup元素
            
        Returns:
            属性名和值的元组列表
        """
        results = []
        
        if not element.name:
            return results
        
        translatable_attrs = {
            'alt': '图片替代文本',
            'title': '标题提示',
            'aria-label': 'ARIA标签',
            'placeholder': '占位符文本',
            'value': '默认值',
            'data-tooltip': '工具提示',
            'data-title': '标题数据'
        }
        
        for attr_name, attr_desc in translatable_attrs.items():
            attr_value = element.get(attr_name)
            if attr_value and isinstance(attr_value, str) and attr_value.strip():
                # 检查是否应该翻译这个属性
                if self._should_translate_attribute(attr_name, attr_value):
                    results.append((attr_name, attr_value))
        
        return results
    
    def _should_translate_attribute(self, attr_name: str, attr_value: str) -> bool:
        """判断属性是否应该翻译
        
        Args:
            attr_name: 属性名
            attr_value: 属性值
            
        Returns:
            是否应该翻译
        """
        # 检查是否包含URL
        if self._is_url(attr_value):
            return False
        
        # 检查是否像代码
        if self._is_code_like(attr_value):
            return False
        
        # 检查是否只是文件名或路径
        if re.match(r'^[a-zA-Z0-9\-_]+\.(css|js|png|jpg|jpeg|gif|svg|ico)$', attr_value):
            return False
        
        return True
    
    def _filter_translatable_texts(self, texts: List[str]) -> List[Tuple[int, str]]:
        """过滤出真正需要翻译的文本
        
        Args:
            texts: 原始文本列表
            
        Returns:
            需要翻译的文本及索引的元组列表
        """
        translatable = []
        
        for i, text in enumerate(texts):
            clean_text = text.strip()
            
            if not clean_text:
                continue
            
            # 跳过短文本（可能是标题或缩写）
            if len(clean_text) < 2:
                continue
            
            # 跳过纯数字
            if clean_text.isdigit():
                continue
            
            # 跳过已经是中文的文本
            if self._is_chinese_text(clean_text):
                continue
            
            # 跳过URL
            if self._is_url(clean_text):
                continue
            
            # 跳过代码样式的文本
            if self._is_code_like(clean_text):
                continue
            
            translatable.append((i, clean_text))
        
        return translatable
    
    def _split_text(self, text: str) -> List[str]:
        """将长文本拆分为符合模型token限制的小块
        
        Args:
            text: 待拆分的长文本
            
        Returns:
            拆分后的文本块列表
        """
        if not text:
            return []
            
        # 估算当前文本的token数量
        estimated_tokens = self.token_tracker.estimate_tokens(text)
        
        # 如果不超过限制，直接返回
        if estimated_tokens <= self.MAX_TOKEN_PER_TEXT:
            return [text]
            
        # 尝试按句子拆分
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        
        # 合并句子，确保每个块不超过token限制
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.token_tracker.estimate_tokens(sentence)
            
            # 如果单个句子就超过限制，进一步按段落拆分
            if sentence_tokens > self.MAX_TOKEN_PER_TEXT:
                paragraphs = sentence.split('\n\n')
                
                for paragraph in paragraphs:
                    paragraph_tokens = self.token_tracker.estimate_tokens(paragraph)
                    
                    # 如果单个段落仍超过限制，按逗号拆分
                    if paragraph_tokens > self.MAX_TOKEN_PER_TEXT:
                        segments = paragraph.split(',')
                        
                        for segment in segments:
                            segment_tokens = self.token_tracker.estimate_tokens(segment)
                            
                            if segment_tokens > self.MAX_TOKEN_PER_TEXT:
                                # 极端情况：按空格拆分
                                words = segment.split()
                                temp_chunk = ""
                                temp_tokens = 0
                                
                                for word in words:
                                    word_tokens = self.token_tracker.estimate_tokens(word + ' ')
                                    
                                    if temp_tokens + word_tokens > self.MAX_TOKEN_PER_TEXT and temp_chunk:
                                        chunks.append(temp_chunk.strip())
                                        temp_chunk = ""
                                        temp_tokens = 0
                                        
                                    temp_chunk += word + ' '
                                    temp_tokens += word_tokens
                                    
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                            else:
                                chunks.append(segment.strip() + ',')
                    else:
                        chunks.append(paragraph.strip())
            else:
                # 合并句子
                new_tokens = current_tokens + sentence_tokens
                
                if new_tokens > self.MAX_TOKEN_PER_TEXT:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                else:
                    current_chunk += ' ' + sentence if current_chunk else sentence
                    current_tokens = new_tokens
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        # 清理可能的重复标点
        chunks = [re.sub(r'([.!?。！？,])\1+', r'\1', chunk) for chunk in chunks]
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        
        return chunks

    def _is_chinese_text(self, text: str) -> bool:
        """判断文本是否主要为中文
        
        Args:
            text: 待检查文本
            
        Returns:
            是否主要为中文
        """
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        
        # 如果中文字符超过50%，认为不需要翻译
        return chinese_chars / total_chars > 0.5 if total_chars > 0 else False
    
    async def _translate_texts_batch(self, texts: List[str], source_lang: Optional[str],
                                    target_lang: str) -> List[str]:
        """批量翻译文本
        
        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            翻译后的文本列表
        """
        if not texts:
            return []
        
        translated_results = []
        
        for text in texts:
            # 拆分长文本
            chunks = self._split_text(text)
            
            # 翻译所有拆分后的文本块
            try:
                chunk_results = await self.translator.translate_batch(
                    texts=chunks,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                
                # 合并翻译结果
                translated_text = ' '.join(chunk_results)
                
                # 检查是否有翻译失败的标记
                if '[TRANSLATION_FAILED]' in translated_text:
                    # 如果有翻译失败的块，返回原文
                    translated_results.append(text)
                else:
                    translated_results.append(translated_text)
                    
            except Exception as e:
                logger.error(f"翻译文本块失败: {e}")
                # 返回原文作为回退
                translated_results.append(text)
        
        return translated_results
    
    async def process_file(self, input_file: str, output_file: str = None,
                          source_lang: Optional[str] = None, 
                          target_lang: str = "zh") -> Dict[str, Any]:
        """翻译HTML文件
        
        Args:
            input_file: 输入HTML文件路径
            output_file: 输出HTML文件路径（默认覆盖原文件）
            source_lang: 源语言代码（可选）
            target_lang: 目标语言代码（必选）
            
        Returns:
            翻译结果统计信息
        """
        try:
            logger.info(f"开始处理HTML文件: {input_file}")
            
            # 读取HTML文件
            with open(input_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 提取并保存 XML 声明（如果存在）
            xml_declaration = None
            xml_decl_pattern = re.compile(r'^<\?xml[^?]*\?>\s*', re.IGNORECASE)
            xml_match = xml_decl_pattern.match(html_content)
            if xml_match:
                xml_declaration = xml_match.group(0).rstrip()
                html_content = html_content[xml_match.end():]
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取所有可翻译的文本节点
            text_nodes = self._extract_text_nodes(soup)
            
            if not text_nodes:
                logger.info("HTML文件中没有找到需要翻译的文本")
                return {
                    'success': True,
                    'original_text_count': 0,
                    'translated_count': 0,
                    'skipped_count': 0
                }
            
            logger.info(f"找到 {len(text_nodes)} 个文本节点")
            
            # 收集所有待翻译文本
            all_texts = []
            text_mapping = []  # 记录原文本索引
            
            for text_node, tag_name in text_nodes:
                text = str(text_node.string).strip()
                if text:
                    all_texts.append(text)
                    text_mapping.append((text_node, tag_name))
            
            # 过滤真正需要翻译的文本
            translatable_indices = self._filter_translatable_texts(all_texts)
            
            if not translatable_indices:
                logger.info("没有找到需要翻译的文本内容")
                return {
                    'success': True,
                    'original_text_count': len(all_texts),
                    'translated_count': 0,
                    'skipped_count': len(all_texts)
                }
            
            logger.info(f"过滤后有 {len(translatable_indices)} 个文本需要翻译")
            
            # 提取待翻译文本
            texts_to_translate = [text for _, text in translatable_indices]
            
            # 执行翻译
            translated_texts = await self._translate_texts_batch(
                texts_to_translate, source_lang, target_lang
            )
            
            # 回填翻译结果
            translated_count = 0
            for i, (original_index, _) in enumerate(translatable_indices):
                if i < len(translated_texts):
                    translated_text = translated_texts[i]
                    if translated_text:
                        text_node, _ = text_mapping[original_index]
                        text_node.replace_with(translated_text)
                        translated_count += 1
            
            # 处理可翻译的属性
            await self._process_attributes(soup, source_lang, target_lang)
            
            # 保存结果
            output_path = output_file or input_file
            with open(output_path, 'w', encoding='utf-8') as f:
                # 恢复 XML 声明（如果原文件有）
                if xml_declaration:
                    f.write(xml_declaration + '\n')
                f.write(str(soup))
            
            logger.info(f"HTML翻译完成: {translated_count} 个文本翻译成功")
            
            return {
                'success': True,
                'original_text_count': len(all_texts),
                'translated_count': translated_count,
                'skipped_count': len(all_texts) - translated_count,
                'output_file': output_path
            }
            
        except Exception as e:
            logger.error(f"处理HTML文件失败: {e}")
            raise FileProcessingError(f"处理HTML文件失败: {e}")
    
    async def _process_attributes(self, soup: BeautifulSoup, source_lang: Optional[str], 
                                target_lang: str):
        """处理可翻译的属性
        
        Args:
            soup: BeautifulSoup对象
            source_lang: 源语言代码
            target_lang: 目标语言代码
        """
        try:
            # 找到所有具有可翻译属性的元素
            elements_with_attrs = []
            
            for element in soup.find_all(True):
                attrs = self._extract_translatable_attributes(element)
                if attrs:
                    elements_with_attrs.append((element, attrs))
            
            if not elements_with_attrs:
                return
            
            logger.info(f"发现 {len(elements_with_attrs)} 个元素有可翻译属性")
            
            # 收集所有属性文本
            attr_texts = []
            attr_mapping = []  # 记录元素和属性名
            
            for element, attrs in elements_with_attrs:
                for attr_name, attr_value in attrs:
                    attr_texts.append(attr_value)
                    attr_mapping.append((element, attr_name))
            
            # 过滤可翻译的属性文本
            translatable_attr_indices = self._filter_translatable_texts(attr_texts)
            
            if not translatable_attr_indices:
                return
            
            # 提取待翻译的属性文本
            texts_to_translate = [text for _, text in translatable_attr_indices]
            
            # 翻译属性文本
            translated_attrs = await self._translate_texts_batch(
                texts_to_translate, source_lang, target_lang
            )
            
            # 回填翻译结果
            for i, (original_index, _) in enumerate(translatable_attr_indices):
                if i < len(translated_attrs):
                    translated_text = translated_attrs[i]
                    if translated_text:
                        element, attr_name = attr_mapping[original_index]
                        element[attr_name] = translated_text
            
            logger.info("属性翻译完成")
            
        except Exception as e:
            logger.error(f"处理可翻译属性失败: {e}")
            # 属性翻译失败不影响主流程
