#!/usr/bin/env python3
"""
EPUB 漏译检测工具
检查 EPUB 文件中是否还有未翻译的英文段落
"""

import zipfile
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString
from typing import List, Dict, Tuple

class EPUBTranslationChecker:
    """EPUB 翻译完整性检查器"""
    
    def __init__(self):
        # 块级标签，我们要检查这些标签内的文本
        self.block_tags = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'blockquote'}
        
        # 忽略的标签（不检查其内容）
        self.exclude_tags = {
            'script', 'style', 'code', 'pre', 'textarea', 'noscript',
            'meta', 'link', 'title', 'head', 'svg', 'path'
        }
        
    def _is_chinese_dominant(self, text: str) -> bool:
        """判断文本是否主要为中文（超过30%即视为已翻译）"""
        if not text:
            return False
        chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        return (chinese_count / total_chars) > 0.3 if total_chars > 0 else False
    
    def _is_meaningful_english(self, text: str) -> bool:
        """判断是否为有意义的英文文本（需要翻译的）"""
        text = text.strip()
        
        # 过滤：太短
        if len(text) < 5:
            return False
        
        # 过滤：纯数字
        if text.replace('.', '').replace(',', '').replace('-', '').replace(' ', '').isdigit():
            return False
        
        # 过滤：URL
        if re.match(r'^https?://', text) or 'www.' in text:
            return False
        
        # [新增] 过滤：邮箱地址
        if re.search(r'[\w.-]+@[\w.-]+\.\w+', text):
            return False
        
        # [新增] 过滤：看起来像域名 (xxx.com, xxx.org 等)
        if re.match(r'^[\w.-]+\.(com|org|net|io|co|edu|gov|us|uk|cn)$', text, re.I):
            return False
        
        # [新增] 过滤：ISBN 编号
        if re.search(r'ISBN[\s:-]*[\d-]{10,}', text, re.I):
            return False
        
        # 过滤：看起来像代码
        if re.search(r'[{}[\]<>=;]', text) and len(text) < 100:
            return False
        
        # 过滤：大量符号（可能是代码或特殊标记）
        symbols = len(re.findall(r'[^a-zA-Z0-9\s\.,!?\-\'\"()]', text))
        if symbols > len(text) * 0.3:  # 超过30%是特殊符号
            return False
        
        # 检查是否包含足够的英文字母
        english_letters = len(re.findall(r'[a-zA-Z]', text))
        if english_letters < 3:
            return False
        
        # [修改] 提高门槛：至少3个英文单词才认为需要翻译
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        if len(words) < 3:  # 从 2 改为 3
            return False
        
        # [新增] 如果文本中有足够多的中文字符(超过20%)，可能是中英混合的版权信息，不算漏译
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > 0 and (chinese_chars / len(text)) > 0.2:
            return False
        
        return True
    
    def check_html_content(self, html_content: str, filename: str) -> List[Dict]:
        """检查单个 HTML 文件的翻译情况
        
        Returns:
            List of dicts with keys: 'file', 'tag', 'text', 'context'
        """
        untranslated = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            print(f"⚠️  无法解析 {filename}: {e}")
            return untranslated
        
        # 查找所有块级元素
        for block in soup.find_all(self.block_tags):
            # 跳过被排除的父标签
            if any(parent.name in self.exclude_tags for parent in block.parents):
                continue
            
            # 获取完整文本
            full_text = block.get_text(" ", strip=True)
            
            if not full_text:
                continue
            
            # 如果已经是中文为主，跳过
            if self._is_chinese_dominant(full_text):
                continue
            
            # 检查是否为有意义的英文
            if self._is_meaningful_english(full_text):
                # 提取上下文（前后20个字符）
                context = self._extract_context(block)
                
                untranslated.append({
                    'file': filename,
                    'tag': block.name,
                    'text': full_text[:200],  # 只取前200字符避免过长
                    'full_text': full_text,   # 保留完整文本
                    'context': context
                })
        
        return untranslated
    
    def _extract_context(self, element) -> str:
        """提取元素的上下文（前一个和后一个兄弟节点的部分文本）"""
        context_parts = []
        
        # 前一个兄弟
        prev = element.find_previous_sibling()
        if prev:
            prev_text = prev.get_text(" ", strip=True)
            if prev_text:
                context_parts.append(f"...{prev_text[-30:]}")
        
        # 当前元素的类名
        classes = element.get('class', [])
        if classes:
            context_parts.append(f"[class={' '.join(classes)}]")
        
        # 后一个兄弟
        next_elem = element.find_next_sibling()
        if next_elem:
            next_text = next_elem.get_text(" ", strip=True)
            if next_text:
                context_parts.append(f"{next_text[:30]}...")
        
        return " | ".join(context_parts) if context_parts else ""
    
    def check_epub(self, epub_path: str) -> Dict:
        """检查整个 EPUB 文件
        
        Returns:
            Dict with keys: 'total_files', 'untranslated_count', 'details'
        """
        epub_path = Path(epub_path)
        
        if not epub_path.exists():
            raise FileNotFoundError(f"找不到文件: {epub_path}")
        
        if not epub_path.suffix.lower() == '.epub':
            raise ValueError("文件必须是 .epub 格式")
        
        print(f"📖 正在检查: {epub_path.name}")
        print("=" * 60)
        
        all_untranslated = []
        checked_files = 0
        
        try:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                # 获取所有 HTML/XHTML 文件
                html_files = [
                    name for name in zf.namelist()
                    if name.endswith(('.html', '.xhtml', '.htm'))
                    and not name.startswith('__MACOSX')  # 排除 macOS 元数据
                ]
                
                print(f"📄 找到 {len(html_files)} 个 HTML 文件\n")
                
                for html_file in html_files:
                    try:
                        content = zf.read(html_file).decode('utf-8')
                        untranslated = self.check_html_content(content, html_file)
                        
                        if untranslated:
                            all_untranslated.extend(untranslated)
                            print(f"⚠️  {html_file}: 发现 {len(untranslated)} 处未翻译")
                        else:
                            print(f"✅ {html_file}: 无漏译")
                        
                        checked_files += 1
                        
                    except Exception as e:
                        print(f"❌ {html_file}: 检查失败 - {e}")
        
        except zipfile.BadZipFile:
            raise ValueError("文件不是有效的 EPUB (ZIP) 格式")
        
        return {
            'total_files': checked_files,
            'untranslated_count': len(all_untranslated),
            'details': all_untranslated
        }
    
    def generate_report(self, result: Dict, output_file: str = None):
        """生成详细报告"""
        print("\n" + "=" * 60)
        print("📊 检查结果汇总")
        print("=" * 60)
        print(f"✅ 检查文件数: {result['total_files']}")
        print(f"⚠️  漏译段落数: {result['untranslated_count']}")
        
        if result['untranslated_count'] == 0:
            print("\n🎉 恭喜！未发现漏译！")
            return
        
        print("\n" + "=" * 60)
        print("📋 详细漏译列表")
        print("=" * 60)
        
        # 按文件分组
        by_file = {}
        for item in result['details']:
            filename = item['file']
            if filename not in by_file:
                by_file[filename] = []
            by_file[filename].append(item)
        
        report_lines = []
        
        for filename, items in sorted(by_file.items()):
            print(f"\n📄 {filename} ({len(items)} 处)")
            report_lines.append(f"\n{'='*80}\n文件: {filename}\n{'='*80}\n")
            
            for i, item in enumerate(items, 1):
                print(f"\n  [{i}] <{item['tag']}>")
                print(f"      {item['text']}")
                if item['context']:
                    print(f"      上下文: {item['context']}")
                
                report_lines.append(
                    f"\n[{i}] 标签: <{item['tag']}>\n"
                    f"内容:\n{item['full_text']}\n"
                    f"上下文: {item['context']}\n"
                    f"{'-'*80}\n"
                )
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("EPUB 漏译检测报告\n")
                f.write(f"生成时间: {Path(epub_path).name}\n")
                f.write(f"总文件数: {result['total_files']}\n")
                f.write(f"漏译段落: {result['untranslated_count']}\n")
                f.writelines(report_lines)
            print(f"\n💾 详细报告已保存至: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("用法: uv run python tools/check_untranslated.py <epub文件路径> [输出报告路径]")
        print("示例: uv run python tools/check_untranslated.py /path/to/book.epub report.txt")
        sys.exit(1)
    
    epub_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    checker = EPUBTranslationChecker()
    
    try:
        result = checker.check_epub(epub_path)
        checker.generate_report(result, output_file)
        
        # 返回适当的退出码
        sys.exit(0 if result['untranslated_count'] == 0 else 1)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()
