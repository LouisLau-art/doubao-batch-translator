#!/usr/bin/env python3
"""
Markdown处理器 - 翻译Markdown文件，保留结构
特性：代码块保护、链接URL保护、YAML Frontmatter处理
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import mistune
import yaml

from core.client import AsyncTranslator

logger = logging.getLogger(__name__)


class MarkdownProcessor:
    """Markdown文件翻译处理器"""
    
    # YAML frontmatter 中需要翻译的字段
    TRANSLATABLE_FRONTMATTER_KEYS = {'title', 'description', 'summary', 'subtitle'}
    
    def __init__(self, translator: AsyncTranslator):
        self.translator = translator
        self._markdown = mistune.create_markdown(renderer=None)
    
    def _extract_frontmatter(self, content: str) -> Tuple[Optional[Dict], str]:
        """
        提取YAML frontmatter和正文内容
        返回: (frontmatter_dict or None, body_content)
        """
        if not content.startswith('---'):
            return None, content
        
        # 查找结束的 ---
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return None, content
        
        end_pos = end_match.end() + 3
        frontmatter_str = content[4:end_match.start() + 3]
        body = content[end_pos:]
        
        try:
            frontmatter = yaml.safe_load(frontmatter_str)
            return frontmatter, body
        except yaml.YAMLError:
            logger.warning("无法解析 YAML frontmatter，跳过")
            return None, content
    
    def _rebuild_frontmatter(self, frontmatter: Dict) -> str:
        """重建 YAML frontmatter 字符串"""
        return '---\n' + yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False) + '---\n'
    
    def _parse_tokens(self, markdown_content: str) -> List[Dict]:
        """解析Markdown为token列表"""
        return self._markdown(markdown_content)
    
    def _extract_translatable_segments(self, tokens: List[Dict]) -> List[Tuple[int, str, Dict]]:
        """
        从token树中提取可翻译的文本段
        返回: [(index, text, token_ref), ...]
        """
        segments = []
        
        def walk(token_list: List[Dict], parent_type: str = None):
            for i, token in enumerate(token_list):
                token_type = token.get('type', '')
                
                # 跳过代码块和内联代码
                if token_type in ('code_block', 'block_code', 'codespan'):
                    continue
                
                # 处理纯文本
                if token_type == 'text':
                    raw = token.get('raw', '')
                    if raw.strip():
                        segments.append((len(segments), raw, token))
                
                # 处理链接 - 只翻译 children 中的文本
                elif token_type == 'link':
                    children = token.get('children', [])
                    for child in children:
                        if child.get('type') == 'text':
                            raw = child.get('raw', '')
                            if raw.strip():
                                segments.append((len(segments), raw, child))
                
                # 处理图片 alt 文本
                elif token_type == 'image':
                    alt = token.get('alt', '')
                    if alt.strip():
                        # 图片的alt存储在token自身
                        segments.append((len(segments), alt, {'_image_token': token, 'type': 'image_alt'}))
                
                # 递归处理子节点
                children = token.get('children')
                if children and isinstance(children, list):
                    walk(children, token_type)
        
        walk(tokens)
        return segments
    
    def _apply_translations(self, segments: List[Tuple[int, str, Dict]], translations: List[str]):
        """将翻译结果回填到token引用"""
        for (idx, original, token_ref), translated in zip(segments, translations):
            if translated and translated != "[TRANSLATION_FAILED]":
                if token_ref.get('type') == 'image_alt':
                    # 处理图片alt
                    image_token = token_ref.get('_image_token')
                    if image_token:
                        image_token['alt'] = translated
                else:
                    # 普通文本token
                    token_ref['raw'] = translated
    
    def _tokens_to_markdown(self, tokens: List[Dict]) -> str:
        """将token树重新转换为Markdown文本"""
        output = []
        
        def render(token_list: List[Dict]):
            for token in token_list:
                token_type = token.get('type', '')
                raw = token.get('raw', '')
                
                if token_type == 'paragraph':
                    children = token.get('children', [])
                    para_text = ''.join(render_inline(children))
                    output.append(para_text + '\n\n')
                
                elif token_type == 'heading':
                    level = token.get('attrs', {}).get('level', 1)
                    children = token.get('children', [])
                    heading_text = ''.join(render_inline(children))
                    output.append('#' * level + ' ' + heading_text + '\n\n')
                
                elif token_type in ('code_block', 'block_code'):
                    info = token.get('attrs', {}).get('info', '') or token.get('info', '')
                    code = token.get('raw', '')
                    output.append(f'```{info}\n{code}```\n\n')
                
                elif token_type == 'list':
                    children = token.get('children', [])
                    ordered = token.get('attrs', {}).get('ordered', False)
                    for i, item in enumerate(children):
                        prefix = f'{i+1}. ' if ordered else '- '
                        item_children = item.get('children', [])
                        item_text = ''.join(render_inline_recursive(item_children))
                        output.append(prefix + item_text + '\n')
                    output.append('\n')
                
                elif token_type == 'blockquote':
                    children = token.get('children', [])
                    quote_text = ''.join(render_inline_recursive(children))
                    for line in quote_text.strip().split('\n'):
                        output.append('> ' + line + '\n')
                    output.append('\n')
                
                elif token_type == 'thematic_break':
                    output.append('---\n\n')
                
                elif token_type == 'blank_line':
                    output.append('\n')
                
                else:
                    # 默认处理
                    children = token.get('children')
                    if children:
                        render(children)
                    elif raw:
                        output.append(raw)
        
        def render_inline(tokens: List[Dict]) -> List[str]:
            result = []
            for t in tokens:
                t_type = t.get('type', '')
                raw = t.get('raw', '')
                
                if t_type == 'text':
                    result.append(raw)
                elif t_type == 'codespan':
                    result.append(f'`{raw}`')
                elif t_type == 'emphasis':
                    children = t.get('children', [])
                    inner = ''.join(render_inline(children))
                    result.append(f'*{inner}*')
                elif t_type == 'strong':
                    children = t.get('children', [])
                    inner = ''.join(render_inline(children))
                    result.append(f'**{inner}**')
                elif t_type == 'link':
                    children = t.get('children', [])
                    text = ''.join(render_inline(children))
                    url = t.get('attrs', {}).get('url', '') or t.get('link', '')
                    title = t.get('attrs', {}).get('title', '')
                    if title:
                        result.append(f'[{text}]({url} "{title}")')
                    else:
                        result.append(f'[{text}]({url})')
                elif t_type == 'image':
                    alt = t.get('alt', '')
                    src = t.get('attrs', {}).get('url', '') or t.get('src', '')
                    result.append(f'![{alt}]({src})')
                elif t_type == 'softbreak':
                    result.append('\n')
                elif t_type == 'linebreak':
                    result.append('  \n')
                else:
                    result.append(raw)
            return result
        
        def render_inline_recursive(tokens: List[Dict]) -> List[str]:
            result = []
            for t in tokens:
                children = t.get('children')
                if children:
                    result.extend(render_inline(children))
                else:
                    result.extend(render_inline([t]))
            return result
        
        render(tokens)
        return ''.join(output)
    
    async def translate_file(
        self, 
        input_file: str, 
        output_file: str = None,
        source_lang: str = "en", 
        target_lang: str = "zh"
    ) -> Dict[str, Any]:
        """
        翻译Markdown文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径 (默认覆盖原文件)
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            统计信息字典
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path
        
        logger.info(f"处理Markdown: {input_path}")
        
        # 读取文件
        content = input_path.read_text(encoding='utf-8')
        
        # 1. 提取 frontmatter
        frontmatter, body = self._extract_frontmatter(content)
        frontmatter_translated_count = 0
        
        if frontmatter:
            # 翻译 frontmatter 中的指定字段
            fm_texts = []
            fm_keys = []
            for key in self.TRANSLATABLE_FRONTMATTER_KEYS:
                if key in frontmatter and isinstance(frontmatter[key], str):
                    fm_texts.append(frontmatter[key])
                    fm_keys.append(key)
            
            if fm_texts:
                logger.info(f"翻译 frontmatter 字段: {fm_keys}")
                fm_translations = await self.translator.translate_batch(fm_texts, source_lang, target_lang)
                for key, trans in zip(fm_keys, fm_translations):
                    if trans and trans != "[TRANSLATION_FAILED]":
                        frontmatter[key] = trans
                        frontmatter_translated_count += 1
        
        # 2. 解析 Markdown body
        tokens = self._parse_tokens(body)
        
        # 3. 提取可翻译段落
        segments = self._extract_translatable_segments(tokens)
        
        if not segments:
            logger.info("无需翻译的内容")
            return {
                'success': True,
                'translated_count': frontmatter_translated_count,
                'output_file': str(output_path)
            }
        
        logger.info(f"提取到 {len(segments)} 个可翻译文本段")
        
        # 4. 批量翻译
        texts_to_translate = [seg[1] for seg in segments]
        
        # 分批处理 (每批50个)
        batch_size = 50
        all_translations = []
        
        for i in range(0, len(texts_to_translate), batch_size):
            batch = texts_to_translate[i:i+batch_size]
            batch_trans = await self.translator.translate_batch(batch, source_lang, target_lang)
            all_translations.extend(batch_trans)
            
            progress = min((i + batch_size) / len(texts_to_translate) * 100, 100)
            print(f"\rMarkdown 翻译进度: {progress:.1f}%", end="", flush=True)
        
        print()  # 换行
        
        # 5. 回填翻译结果
        self._apply_translations(segments, all_translations)
        
        # 6. 重建 Markdown
        translated_body = self._tokens_to_markdown(tokens)
        
        # 7. 组合输出
        if frontmatter:
            final_content = self._rebuild_frontmatter(frontmatter) + '\n' + translated_body
        else:
            final_content = translated_body
        
        # 8. 写入文件
        output_path.write_text(final_content, encoding='utf-8')
        
        translated_count = sum(1 for t in all_translations if t and t != "[TRANSLATION_FAILED]")
        
        logger.info(f"Markdown翻译完成! 已翻译 {translated_count + frontmatter_translated_count} 个文本段")
        
        return {
            'success': True,
            'translated_count': translated_count + frontmatter_translated_count,
            'total_segments': len(segments),
            'output_file': str(output_path)
        }
