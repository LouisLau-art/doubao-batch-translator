#!/usr/bin/env python3
"""
ePub 翻译前后对比工具
"""

import zipfile
import tempfile
import os
import shutil
from xml.etree import ElementTree as ET

def extract_epub_info(epub_path):
    """提取 ePub 文件信息"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(epub_path, 'r') as zf:
            zf.extractall(temp_dir)
        
        # 读取 OPF 文件
        container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
        container_tree = ET.parse(container_path)
        container_root = container_tree.getroot()
        
        # 找到 OPF 文件
        rootfile = container_root.find('.//container:rootfile', {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'})
        opf_path = os.path.join(temp_dir, rootfile.get('full-path'))
        
        opf_tree = ET.parse(opf_path)
        opf_root = opf_tree.getroot()
        
        # 提取标题
        title_elem = opf_root.find('.//{http://purl.org/dc/elements/1.1/}title')
        title = title_elem.text if title_elem is not None else "无标题"
        
        # 提取描述
        desc_elem = opf_root.find('.//{http://purl.org/dc/elements/1.1/}description')
        description = desc_elem.text if desc_elem is not None else "无描述"
        
        # 读取 NCX 目录
        ncx_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.ncx'):
                    ncx_files.append(os.path.join(root, file))
        
        nav_items = []
        if ncx_files:
            ncx_tree = ET.parse(ncx_files[0])
            ncx_root = ncx_tree.getroot()
            for nav_point in ncx_root.findall('.//{http://www.daisy.org/z3986/2005/ncx/}navPoint'):
                nav_label = nav_point.find('.//{http://www.daisy.org/z3986/2005/ncx/}text')
                if nav_label is not None and nav_label.text:
                    nav_items.append(nav_label.text)
        
        # 读取第一个 HTML 文件的前几行
        html_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.html', '.xhtml')):
                    html_files.append(os.path.join(root, file))
        
        content_preview = ""
        if html_files:
            with open(html_files[0], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 提取标题和前几段文本
                for line in lines:
                    if '<h1>' in line or '<title>' in line:
                        content_preview += line.strip()
                    elif '<p>' in line and len(content_preview) < 500:
                        content_preview += line.strip()
        
        return {
            'title': title,
            'description': description,
            'nav_items': nav_items,
            'content_preview': content_preview,
            'file_count': len(html_files)
        }

def compare_epubs(original_path, translated_path):
    """对比两个 ePub 文件"""
    print("🔍 正在分析文件...")
    
    original_info = extract_epub_info(original_path)
    translated_info = extract_epub_info(translated_path)
    
    print(f"\n{'='*60}")
    print(f"📚 翻译前后对比报告")
    print(f"{'='*60}")
    
    print(f"\n📖 书籍标题对比:")
    print(f"   原版: {original_info['title']}")
    print(f"   译版: {translated_info['title']}")
    
    print(f"\n📝 描述对比:")
    print(f"   原版: {original_info['description'][:100]}...")
    print(f"   译版: {translated_info['description'][:100]}...")
    
    print(f"\n🗂️  目录对比:")
    print(f"   原版目录:")
    for i, item in enumerate(original_info['nav_items'], 1):
        print(f"     {i}. {item}")
    
    print(f"   译版目录:")
    for i, item in enumerate(translated_info['nav_items'], 1):
        print(f"     {i}. {item}")
    
    print(f"\n📄 内容预览:")
    print(f"   原版前200字符:")
    print(f"   {original_info['content_preview'][:200]}...")
    
    print(f"   译版前200字符:")
    print(f"   {translated_info['content_preview'][:200]}...")
    
    print(f"\n📊 统计信息:")
    print(f"   原版文件: {original_info['file_count']} 个 HTML 文件")
    print(f"   译版文件: {translated_info['file_count']} 个 HTML 文件")
    
    # 检查翻译效果
    title_translated = original_info['title'] != translated_info['title']
    desc_translated = original_info['description'] != translated_info['description']
    nav_translated = any(orig != trans for orig, trans in zip(original_info['nav_items'], translated_info['nav_items']))
    
    print(f"\n✅ 翻译验证:")
    print(f"   标题翻译: {'✅' if title_translated else '❌'}")
    print(f"   描述翻译: {'✅' if desc_translated else '❌'}")
    print(f"   目录翻译: {'✅' if nav_translated else '❌'}")
    print(f"   内容翻译: {'✅' if 'Welcome' not in translated_info['content_preview'] else '⚠️ 部分'}")
    
    if title_translated or desc_translated or nav_translated:
        print(f"\n🎉 翻译成功！ePub 文件已成功翻译。")
    else:
        print(f"\n⚠️  翻译可能存在问题，请检查 API 配置。")

def main():
    """主函数"""
    original_file = "test_book.epub"
    translated_file = "translated_test_book.epub"
    
    if not os.path.exists(original_file):
        print(f"❌ 找不到原文件: {original_file}")
        return
    
    if not os.path.exists(translated_file):
        print(f"❌ 找不到翻译后的文件: {translated_file}")
        return
    
    compare_epubs(original_file, translated_file)

if __name__ == "__main__":
    main()