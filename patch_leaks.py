#!/usr/bin/env python3
"""
EPUB 漏译精准修补工具 (Surgical Patcher)
结合 check_untranslated.py 的检测结果，只重跑有问题的章节。
"""

import sys
import os
import shutil
import asyncio
import logging
import tempfile
import zipfile
from pathlib import Path

# 导入现有模块
from core.config import TranslatorConfig
from core.client import AsyncTranslator
from processors.html_worker import HTMLProcessor
from check_untranslated import EPUBTranslationChecker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Patcher")

async def patch_epub(input_path: str, output_path: str, config: TranslatorConfig):
    """精准修补流程"""
    
    # 1. 诊断阶段
    logger.info("🔍 [阶段1] 正在扫描漏译段落...")
    checker = EPUBTranslationChecker()
    # 捕获 check_epub 的打印输出以免刷屏，或者直接调用逻辑
    try:
        report = checker.check_epub(input_path)
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        return

    untranslated_count = report['untranslated_count']
    if untranslated_count == 0:
        logger.info("🎉 完美！检测结果显示没有漏译，无需修补。")
        return

    # 提取需要修复的文件列表 (去重)
    files_to_fix = set(item['file'] for item in report['details'])
    logger.info(f"⚠️ 发现 {untranslated_count} 处漏译，分布在 {len(files_to_fix)} 个文件中。")
    print(f"   🎯 目标文件: {files_to_fix}")

    # 2. 准备手术环境
    logger.info("🛠️ [阶段2] 准备手术环境...")
    
    # 初始化翻译器
    translator = AsyncTranslator(config)
    processor = HTMLProcessor(translator)

    # 【关键大招】临时放宽过滤条件 (Monkey Patch)
    # 我们假设既然 check_untranslated 把它揪出来了，那它肯定就是该翻而没翻的
    # 所以我们临时废掉 _is_url_or_code，防止 ISBN 或短句再次被跳过
    original_filter = processor._is_url_or_code
    processor._is_url_or_code = lambda text: False 
    logger.info("🔓 已临时解除过滤器限制 (强制翻译模式)")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 解压
        with zipfile.ZipFile(input_path, 'r') as zf:
            zf.extractall(temp_dir)
        
        # 3. 执行外科手术
        logger.info("💉 [阶段3] 开始精准修补...")
        
        tasks = []
        for rel_path in files_to_fix:
            full_path = os.path.join(temp_dir, rel_path)
            if not os.path.exists(full_path):
                logger.warning(f"文件找不到: {rel_path}")
                continue
                
            logger.info(f"   处理文件: {rel_path}")
            # 对这些文件再次运行 process_file
            # 这里的 target_lang='zh' 会触发中文跳过逻辑，所以只会翻译剩下的英文
            tasks.append(
                processor.process_file(full_path, full_path, target_lang="zh")
            )
        
        # 并发执行修复
        await asyncio.gather(*tasks)
        
        # 恢复过滤器 (虽然脚本马上结束了，但这是好习惯)
        processor._is_url_or_code = original_filter

        # 4. 缝合伤口 (重新打包)
        logger.info("📦 [阶段4] 重新打包...")
        repack_epub(temp_dir, output_path)
        logger.info(f"✅ 修补完成！文件已保存至: {output_path}")

def repack_epub(source_dir: str, output_path: str):
    """标准的 ePub 打包逻辑"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype 必须不压缩且在最前
        mimetype_path = os.path.join(source_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        for root, _, files in os.walk(source_dir):
            for f in files:
                if f == 'mimetype': continue
                full_path = os.path.join(root, f)
                arc_name = os.path.relpath(full_path, source_dir)
                zf.write(full_path, arc_name)

def main():
    if len(sys.argv) < 2:
        print("用法: python patch_leaks.py <有漏译的epub路径> [输出路径]")
        sys.exit(1)
        
    input_file = sys.argv[1]
    # 默认输出文件名加 _patched
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        p = Path(input_file)
        output_file = str(p.with_name(f"{p.stem}_patched{p.suffix}"))

    # 加载配置 (复用 core.config)
    try:
        config = TranslatorConfig.from_env()
        # 强制高并发，反正只修几个文件
        config.max_concurrent = 50 
    except Exception as e:
        print(f"配置加载失败: {e}")
        sys.exit(1)

    try:
        asyncio.run(patch_epub(input_file, output_file, config))
    except KeyboardInterrupt:
        print("\n❌ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()