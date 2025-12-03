#!/usr/bin/env python3
"""
测试HTMLProcessor的翻译功能
"""

import asyncio
import logging
from core.client import AsyncTranslator
from processors.html_worker import HTMLProcessor

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_html_processor():
    """测试HTML翻译功能"""
    
    # 初始化翻译器
    translator = AsyncTranslator()
    
    # 创建处理器
    html_processor = HTMLProcessor(translator)
    
    # 测试HTML内容
    test_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Chapter 1: Introduction</h1>
    <p>Welcome to this test ebook designed to demonstrate translation capabilities. This book contains various chapters with English content that will be translated to Chinese using advanced AI translation models.</p>
    <p>The main purpose of this document is to test the integration of ePub processing with our translation system.</p>
</body>
</html>"""
    
    # 保存测试文件
    test_file = "test_html_input.html"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_html)
    
    print(f"原始HTML内容:")
    print(test_html)
    print("\n" + "="*50 + "\n")
    
    try:
        # 翻译HTML文件
        result = await html_processor.process_file(
            input_file=test_file,
            output_file=test_file,
            source_lang="en",
            target_lang="zh"
        )
        
        print(f"翻译结果: {result}")
        
        # 读取翻译后的内容
        with open(test_file, 'r', encoding='utf-8') as f:
            translated_html = f.read()
        
        print(f"翻译后HTML内容:")
        print(translated_html)
        
    except Exception as e:
        print(f"翻译失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        try:
            import os
            os.remove(test_file)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_html_processor())