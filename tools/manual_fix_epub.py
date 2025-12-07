#!/usr/bin/env python3
"""
EPUB 手动精修辅助工具
功能：解压 EPUB -> 等待用户修改 -> 重新打包 (保持 mimetype 首位)
"""

import os
import sys
import zipfile
import shutil
import tempfile
import argparse
from pathlib import Path

def repack_epub(source_dir: str, output_path: str):
    """标准的 EPUB 重打包逻辑"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. 必须首先写入 mimetype，且不能压缩
        mimetype_path = os.path.join(source_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        else:
            print("⚠️  警告: 未找到 mimetype 文件，生成的 epub 可能不标准")
        
        # 2. 写入其他文件
        for root, _, files in os.walk(source_dir):
            for f in files:
                if f == 'mimetype': continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, source_dir)
                zf.write(full_path, rel_path)

def main():
    parser = argparse.ArgumentParser(description="EPUB 手动精修助手")
    parser.add_argument("epub_file", help="要修改的 EPUB 文件路径")
    args = parser.parse_args()

    epub_path = Path(args.epub_file).resolve()
    if not epub_path.exists():
        print(f"❌ 文件不存在: {epub_path}")
        sys.exit(1)

    # 创建工作目录
    work_dir = epub_path.parent / f"{epub_path.stem}_edit_work"
    
    # 如果工作目录已存在，询问是否继续使用
    if work_dir.exists():
        choice = input(f"📂 发现已存在的工作目录: {work_dir}\n   是否继续编辑该目录? (y/n) [n表示重新解压]: ").strip().lower()
        if choice != 'y':
            shutil.rmtree(work_dir)
            work_dir.mkdir()
            print("📦 正在解压 EPUB...")
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(work_dir)
    else:
        work_dir.mkdir()
        print("📦 正在解压 EPUB...")
        with zipfile.ZipFile(epub_path, 'r') as zf:
            zf.extractall(work_dir)

    print("\n" + "="*60)
    print(f"🚀 就绪! 请开始您的手动修改")
    print("="*60)
    print(f"1. 进入目录: {work_dir}")
    print(f"2. 根据 '漏译报告.txt' 找到对应的 HTML 文件进行修改")
    print(f"3. 这一步您可以修改任何内容 (文字、样式、图片等)")
    print("\n💡 修改完成后，请回到这里按下 [回车] 键，我将帮您重新打包。")
    
    input("👉 按 [回车] 开始重新打包 (Ctrl+C 取消)...")

    # 备份原文件
    backup_path = epub_path.with_name(f"{epub_path.stem}_backup{epub_path.suffix}")
    if not backup_path.exists():
        shutil.copy2(epub_path, backup_path)
        print(f"💾 原文件已备份至: {backup_path.name}")

    print("📦 正在重新打包...")
    try:
        repack_epub(str(work_dir), str(epub_path))
        print(f"✅ 更新成功! 文件已覆盖: {epub_path}")
        
        # 询问是否删除临时目录
        # clean = input(f"   是否删除临时工作目录? (y/n): ").lower()
        # if clean == 'y':
        #     shutil.rmtree(work_dir)
        print(f"👋 临时目录保留在: {work_dir} (您可稍后手动删除)")
        
    except Exception as e:
        print(f"❌ 打包失败: {e}")

if __name__ == "__main__":
    main()
