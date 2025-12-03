import zipfile
import re

def check_epub(filename):
    print(f"🔍 正在检查: {filename}")
    with zipfile.ZipFile(filename, 'r') as zf:
        # 1. 检查元数据翻译 (OPF)
        opf = zf.read("OEBPS/content.opf").decode('utf-8')
        if "小王子" in opf or "Test" not in opf: # 假设 "The Little Prince" 被翻成了中文
            print("✅ 元数据(标题/简介) 已翻译")
        else:
            print("⚠️ 元数据似乎未翻译 (需人工确认)")

        # 2. 检查目录翻译 (NCX)
        ncx = zf.read("OEBPS/toc.ncx").decode('utf-8')
        if "章" in ncx or "狐狸" in ncx:
            print("✅ 目录(TOC) 已翻译")
        else:
            print("⚠️ 目录似乎未翻译")

        # 3. 检查正文翻译
        ch1 = zf.read("OEBPS/chapter1.html").decode('utf-8')
        if "六岁" in ch1 or "蟒蛇" in ch1:
            print("✅ 正文内容 已翻译")
        else:
            print("❌ 正文内容未翻译！")
            
        # 4. 检查不该翻译的部分 (no-translate)
        if "should NOT be translated" in ch1:
            print("✅ no-translate 标签工作正常 (原文保留)")
        else:
            print("❌ no-translate 标签被错误翻译了！")

if __name__ == "__main__":
    try:
        check_epub("mini_test_cn.epub")
    except FileNotFoundError:
        print("❌ 未找到输出文件 mini_test_cn.epub，翻译可能失败了。")
