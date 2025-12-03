#!/usr/bin/env python3
"""
基础 ePub 解析测试 - 不需要 API 密钥
"""

import asyncio
import tempfile
import os
import zipfile
from processors.epub_worker import EpubProcessor

def test_epub_structure():
    """测试 ePub 文件结构解析"""
    print("🧪 测试 ePub 文件结构解析...")
    
    # 检查测试文件是否存在
    test_file = "test_book.epub"
    if not os.path.exists(test_file):
        print(f"❌ 测试文件 {test_file} 不存在")
        return False
    
    try:
        # 验证 mimetype 文件位置和压缩方式
        with zipfile.ZipFile(test_file, 'r') as zf:
            file_list = zf.namelist()
            
            # 检查 mimetype 必须是第一个文件
            if file_list[0] != 'mimetype':
                print("❌ mimetype 文件不是 ZIP 中的第一个文件")
                return False
            
            # 检查 mimetype 文件压缩方式（应该是不压缩）
            mimetype_info = zf.getinfo('mimetype')
            if mimetype_info.compress_type != zipfile.ZIP_STORED:
                print("❌ mimetype 文件被压缩了，应该是 ZIP_STORED")
                return False
            
            print("✅ ePub 文件结构验证通过")
            print(f"   文件列表: {file_list}")
            return True
            
    except Exception as e:
        print(f"❌ 文件结构验证失败: {e}")
        return False

def test_epub_parsing():
    """测试 ePub 解析功能"""
    print("\n🧪 测试 ePub 解析功能...")
    
    test_file = "test_book.epub"
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 解压文件
            print("   解压文件...")
            with zipfile.ZipFile(test_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 验证解压结果
            files = os.listdir(temp_dir)
            print(f"   解压后文件: {files}")
            
            # 检查关键文件是否存在
            key_files = ['mimetype', 'META-INF/container.xml', 'content.opf']
            for file in key_files:
                if not os.path.exists(os.path.join(temp_dir, file)):
                    print(f"❌ 缺少关键文件: {file}")
                    return False
            
            print("✅ ePub 文件解析成功")
            return True
            
    except Exception as e:
        print(f"❌ 文件解析失败: {e}")
        return False

def test_epub_processor_class():
    """测试 EpubProcessor 类是否正常工作"""
    print("\n🧪 测试 EpubProcessor 类...")
    
    try:
        # 创建一个模拟的翻译器（不需要实际 API 密钥）
        class MockTranslator:
            async def translate_batch(self, texts, source_lang="en", target_lang="zh"):
                return ["模拟翻译: " + text for text in texts]
        
        mock_translator = MockTranslator()
        
        # 尝试创建 EpubProcessor
        from processors.epub_worker import EpubProcessor
        processor = EpubProcessor(mock_translator)
        
        # 检查关键方法是否存在
        required_methods = ['translate_epub', '_extract_epub', '_parse_opf', '_repack_epub']
        for method in required_methods:
            if not hasattr(processor, method):
                print(f"❌ 缺少关键方法: {method}")
                return False
        
        print("✅ EpubProcessor 类验证通过")
        print(f"   可用方法: {required_methods}")
        return True
        
    except Exception as e:
        print(f"❌ EpubProcessor 类测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("🚀 开始 ePub 翻译功能基础测试\n")
    
    tests = [
        ("文件结构验证", test_epub_structure),
        ("文件解析验证", test_epub_parsing), 
        ("类定义验证", test_epub_processor_class),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 测试结果汇总")
    print(f"{'='*50}")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有基础测试通过！ePub 翻译功能已准备就绪。")
        print("\n📝 使用说明:")
        print("   python main.py epub --file test_book.epub --output translated_book.epub --target-lang zh")
    else:
        print(f"\n⚠️  有 {total-passed} 个测试失败，请检查代码。")
    
    return passed == total

if __name__ == "__main__":
    main()