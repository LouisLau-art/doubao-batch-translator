#!/usr/bin/env python3
"""
HTML处理器 - 块级合并翻译策略 (Block-Level Collapse Strategy)
解决 ePub 中标签(如 pagebreak)切断句子导致翻译质量差或漏译的问题。
"""

import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, NavigableString

# 适配你的项目导入路径
from core.client import AsyncTranslator
from core.token_tracker import TokenTracker
from core.exceptions import FileProcessingError

logger = logging.getLogger(__name__)

class HTMLProcessor:
    """HTML文件翻译处理器"""
    
    def __init__(self, translator: AsyncTranslator):
        self.translator = translator
        # 初始化 TokenTracker 用于估算长度
        self.token_tracker = TokenTracker()
        
        # 适当放宽单个请求的 Token 限制，因为我们现在合并了段落
        # doubao-seed 模型限制是 4k context (输入通常建议 < 1k-2k)
        # 我们设为 1000 是安全的，因为 client.py 里是单请求并发
        self.MAX_TOKEN_PER_BLOCK = 1000  
        
        # 定义"块"标签：这些标签内的文本会被视为一个整体
        self.block_tags = {
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'li', 'div', 'blockquote', 'caption', 'td', 'th'
        }
        
        # 绝对排除的标签
        self.exclude_tags = {
            'script', 'style', 'code', 'pre', 'textarea', 'noscript',
            'meta', 'link', 'title', 'head', 'svg', 'path', 'math'
        }

    def _is_url_or_code(self, text: str) -> bool:
        """判断是否为 URL 或代码块"""
        text = text.strip()
        if not text: return True
        
        # 长度小于 2 的非中文通常不需要翻译
        if len(text) < 2 and not self._is_chinese_text(text):
            return True

        # 简单 URL 特征
        if re.match(r'^(https?|ftp|file)://', text, re.I): return True
        if text.startswith('www.') and '.' in text[4:]: return True
        
        # 简单代码特征 (如果包含大量括号且长度较短)
        if len(text) < 100 and re.search(r'[{}[\]<>=;]{3,}', text):
            return True
            
        return False

    def _is_chinese_text(self, text: str) -> bool:
        """判断是否主要是中文"""
        if not text: return False
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        # 只要有 40% 是中文，就认为是已翻译过的 (放宽一点避免误判)
        return (chinese_chars / total_chars) > 0.4

    def _split_text(self, text: str) -> List[str]:
        """
        [兜底策略] 如果一个段落太长(超过API限制)，必须拆分。
        注意：这会切断上下文，但总比报错好。
        """
        if self.token_tracker.estimate_tokens(text) <= self.MAX_TOKEN_PER_BLOCK:
            return [text]
        
        logger.debug(f"文本过长，触发拆分: {text[:30]}...")
        chunks = []
        current_chunk = ""
        
        # 优先按句号拆分
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        
        for sent in sentences:
            if self.token_tracker.estimate_tokens(current_chunk + sent) > self.MAX_TOKEN_PER_BLOCK:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = sent
                else:
                    # 单个句子都超长？强制按逗号拆
                    sub_parts = re.split(r'([,，])', sent)
                    for part in sub_parts:
                        if self.token_tracker.estimate_tokens(current_chunk + part) > self.MAX_TOKEN_PER_BLOCK:
                             if current_chunk: chunks.append(current_chunk)
                             current_chunk = part
                        else:
                             current_chunk += part
            else:
                current_chunk += " " + sent if current_chunk else sent
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    async def _process_blocks(self, soup: BeautifulSoup, source_lang: str, target_lang: str) -> int:
        """
        核心逻辑：提取块 -> 过滤 -> 翻译 -> 回填
        """
        # 1. 提取所有待翻译块
        # 我们只提取"最底层"的块级元素，避免重复翻译 (例如 div 包含 p，只翻 p)
        all_blocks = soup.find_all(self.block_tags)
        target_blocks = [] # List of (tag_object, text_content)
        
        for block in all_blocks:
            # 规则1: 如果这个块内部还有其他块级标签，跳过它（让子元素去处理）
            if block.find(self.block_tags):
                continue
            
            # 规则2: 排除黑名单标签的子孙
            if any(parent.name in self.exclude_tags for parent in block.parents):
                continue
                
            # 规则3: 检查 class 黑名单
            if any(cls in block.get('class', []) for cls in ['no-translate', 'code']):
                continue

            # 获取合并后的纯文本 (separator=' ' 避免单词粘连)
            full_text = block.get_text(" ", strip=True)
            
            # 规则4: 文本内容过滤
            if not full_text: continue
            if self._is_url_or_code(full_text): continue
            
            # [关键] 只有当目标是中文，且文本已是中文时才跳过
            # 如果目标是英文(比如汉译英)，则不能跳过中文
            if target_lang.startswith('zh') and self._is_chinese_text(full_text):
                continue

            target_blocks.append((block, full_text))

        if not target_blocks:
            logger.info("当前文件没有需要翻译的文本块")
            return 0

        logger.info(f"提取到 {len(target_blocks)} 个文本段落，准备翻译...")

        # 2. 准备发送给 API (处理超长拆分)
        # map: batch_index -> (original_block_index, is_part_of_split)
        # 这里为了简化，我们先尝试不拆分直接发，因为前面调大了 limit。
        # 如果真的遇到超长，_split_text 会处理，但回填逻辑会变复杂。
        # 鉴于 doubao-seed 不支持 batch，我们依靠 AsyncTranslator 的并发
        
        # 扁平化处理：如果一个块被拆分，会有多个 request
        requests_map = [] # List of (block_index, text_chunk)
        
        for i, (block, text) in enumerate(target_blocks):
            chunks = self._split_text(text)
            for chunk in chunks:
                requests_map.append((i, chunk))
        
        texts_to_send = [item[1] for item in requests_map]
        
        # 3. 调用 API (并发)
        try:
            # 调用你的 client.py 里的 translate_batch (它内部实现了 semaphore 并发)
            results = await self.translator.translate_batch(
                texts_to_send,
                source_lang=source_lang,
                target_lang=target_lang
            )
        except Exception as e:
            logger.error(f"API 请求严重错误: {e}")
            return 0

        # 4. 重新组装结果并回填 (Collapse Strategy)
        # 先把结果聚合回 block
        block_translations = {i: [] for i in range(len(target_blocks))}
        
        for idx, result in enumerate(results):
            block_idx = requests_map[idx][0]
            
            # 检查失败
            if result == "[TRANSLATION_FAILED]" or isinstance(result, Exception):
                logger.warning(f"段落翻译失败: {texts_to_send[idx][:30]}...")
                # 失败时回退到原文 chunk
                block_translations[block_idx].append(texts_to_send[idx])
            else:
                block_translations[block_idx].append(result)

        # 5. 执行回填
        success_count = 0
        for i, (block, original_text) in enumerate(target_blocks):
            chunks = block_translations.get(i, [])
            if not chunks: continue
            
            # 合并拆分的翻译结果
            final_translation = " ".join(chunks)
            
            # 简单防愚检查：如果翻译结果和原文一样，或者变为空，就不动 DOM
            if final_translation == original_text:
                continue

            # [核心操作] 
            # 1. 找到块内所有文本节点
            text_nodes = [node for node in block.descendants if isinstance(node, NavigableString)]
            
            if not text_nodes:
                # 如果只有空标签，直接设置 string
                block.string = final_translation
            else:
                # 2. 把翻译结果塞给第一个节点
                text_nodes[0].replace_with(final_translation)
                # 3. 清空后续节点 (保留标签结构)
                for node in text_nodes[1:]:
                    node.replace_with("")
            
            success_count += 1

        return success_count

    async def process_file(self, input_file: str, output_file: str = None,
                          source_lang: Optional[str] = None, 
                          target_lang: str = "zh") -> Dict[str, Any]:
        """入口函数"""
        try:
            logger.info(f"开始处理HTML文件: {input_file}")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # XML 声明保留
            xml_decl = ""
            m = re.match(r'^<\?xml.*?\?>', html_content)
            if m: xml_decl = m.group(0)

            # 使用 lxml 容错能力更强，如果没有则 fallback
            try:
                soup = BeautifulSoup(html_content, 'lxml')
            except:
                soup = BeautifulSoup(html_content, 'html.parser')

            # 处理
            count = await self._process_blocks(soup, source_lang, target_lang)
            
            # 保存
            output_path = output_file or input_file
            with open(output_path, 'w', encoding='utf-8') as f:
                if xml_decl: f.write(xml_decl + '\n')
                f.write(str(soup))
            
            logger.info(f"文件处理完成，更新了 {count} 个段落")
            
            return {
                'success': True,
                'translated_count': count,
                'output_file': output_path
            }
            
        except Exception as e:
            logger.error(f"处理HTML文件失败: {e}", exc_info=True)
            raise FileProcessingError(f"HTML处理失败: {e}")