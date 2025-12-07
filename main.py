#!/usr/bin/env python3
"""
豆包翻译模型统一接口 - 主入口
支持CLI命令行工具、HTTP Server服务、以及智能 ePub 漏译修复闭环
"""

import argparse
import asyncio
import logging
import sys
import os
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict, List

# 确保能找到 core 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import TranslatorConfig
from core.client import AsyncTranslator
from processors.json_worker import JSONProcessor
from processors.html_worker import HTMLProcessor
from processors.epub_worker import EpubProcessor
from server.api import run_server

# 尝试导入质检工具
try:
    from check_untranslated import EPUBTranslationChecker
except ImportError:
    EPUBTranslationChecker = None

# 配置日志
from logging.handlers import RotatingFileHandler

# 日志文件固定在项目目录下
_LOG_FILE = Path(__file__).parent / 'doubao-translator.log'

# 创建格式化器 (包含模块名便于调试)
_log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 控制台处理器 (简洁格式)
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
_console_handler.setLevel(logging.INFO)

# 文件处理器 (带轮转: 10MB, 保留3份)
_file_handler = RotatingFileHandler(
    _LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=3,
    encoding='utf-8'
)
_file_handler.setFormatter(_log_formatter)
_file_handler.setLevel(logging.DEBUG)  # 文件记录更详细

# 配置根日志
logging.basicConfig(level=logging.DEBUG, handlers=[_console_handler, _file_handler])

# 降低第三方库日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class MainCLI:
    """主命令行界面"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建参数解析器"""
        parser = argparse.ArgumentParser(
            description="豆包翻译模型统一接口 - 智能闭环版",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # 通用参数
        parser.add_argument("--api-key", help="豆包API密钥")
        parser.add_argument("--verbose", "-v", action="store_true", help="启用详细日志")
        parser.add_argument("--max-concurrent", type=int, help="最大并发请求数 (建议: 30-100)")
        parser.add_argument("--max-rps", type=float, help="每秒最大请求数 (建议: 20.0)")
        
        # 子命令
        subparsers = parser.add_subparsers(dest="command", help="可用命令")
        
        # JSON翻译命令
        json_parser = subparsers.add_parser("json", help="JSON文件翻译")
        json_parser.add_argument("--file", "-f", required=True, help="输入文件")
        json_parser.add_argument("--output", "-o", help="输出文件")
        json_parser.add_argument("--source-lang", help="源语言")
        json_parser.add_argument("--target-lang", "-t", default="zh", help="目标语言")
        
        # HTML翻译命令
        html_parser = subparsers.add_parser("html", help="HTML文件翻译")
        html_parser.add_argument("--file", "-f", required=True, help="输入文件")
        html_parser.add_argument("--output", "-o", help="输出文件")
        html_parser.add_argument("--source-lang", help="源语言")
        html_parser.add_argument("--target-lang", "-t", default="zh", help="目标语言")
        
        # ePub翻译命令
        epub_parser = subparsers.add_parser("epub", help="ePub电子书翻译")
        epub_parser.add_argument("--file", "-f", required=True, help="输入文件 或 文件夹")
        epub_parser.add_argument("--output", "-o", help="输出文件 或 输出文件夹")
        epub_parser.add_argument("--source-lang", help="源语言")
        epub_parser.add_argument("--target-lang", "-t", default="zh", help="目标语言")
        # [修改] 将 auto-approve 移到这里，作为 epub 子命令的参数
        epub_parser.add_argument("--auto-approve", action="store_true", help="自动同意质检修复，无需人工确认")
        
        # Server命令
        server_parser = subparsers.add_parser("server", help="启动HTTP API服务器")
        server_parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
        server_parser.add_argument("--port", "-p", type=int, default=8000, help="监听端口")
        server_parser.add_argument("--debug", action="store_true", help="启用调试模式")
        
        # [新增] 人工翻译回填命令
        applyfix_parser = subparsers.add_parser("apply-fix", help="将人工翻译的JSON回填到ePub")
        applyfix_parser.add_argument("--json", "-j", required=True, help="人工翻译.json 文件路径")
        
        # [新增] 重新生成漏译 JSON (针对已翻译的 EPUB)
        genjson_parser = subparsers.add_parser("generate-json", help="扫描已翻译EPUB并生成人工翻译JSON")
        genjson_parser.add_argument("--dir", "-d", required=True, help="已翻译EPUB所在目录")
        
        return parser
    
    def _get_config(self, args) -> TranslatorConfig:
        """获取配置对象"""
        config_kwargs = {}
        if hasattr(args, 'max_concurrent') and args.max_concurrent:
            config_kwargs['max_concurrent'] = args.max_concurrent
        if hasattr(args, 'max_rps') and args.max_rps:
            config_kwargs['max_requests_per_second'] = args.max_rps
            
        try:
            return TranslatorConfig.from_args(
                api_key=args.api_key, 
                **config_kwargs
            )
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            sys.exit(1)
    
    def _create_translator(self, config: TranslatorConfig) -> AsyncTranslator:
        """工厂方法"""
        return AsyncTranslator(config)

    def _print_stats(self, translator: AsyncTranslator):
        """打印模型使用统计 (含 Token)"""
        if not hasattr(translator, 'get_stats'):
            return

        stats = translator.get_stats()
        total_requests = 0
        total_in = 0
        total_out = 0
        
        for data in stats.values():
            total_requests += data.get('calls', 0)
            total_in += data.get('input', 0)
            total_out += data.get('output', 0)
        
        if total_requests == 0:
            return

        print("\n" + "="*85)
        print("📊 模型使用统计报告")
        print("="*85)
        print(f"{'模型名称':<35} | {'次数':<6} | {'占比':<6} | {'Input Tokens':<12} | {'Output Tokens':<12}")
        print("-" * 85)
        
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['calls'], reverse=True)
        
        for model, data in sorted_stats:
            count = data.get('calls', 0)
            if count > 0:
                percentage = (count / total_requests) * 100
                in_t = data.get('input', 0)
                out_t = data.get('output', 0)
                print(f"{model:<35} | {count:<6} | {percentage:.1f}%  | {in_t:<12,} | {out_t:<12,}")
        
        print("-" * 85)
        print(f"{'总计':<35} | {total_requests:<6} | 100%   | {total_in:<12,} | {total_out:<12,}")
        print("="*85 + "\n")

    def _repack_epub(self, source_dir: str, output_path: str):
        """重新打包 ePub 工具函数"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            mimetype_path = os.path.join(source_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            for root, _, files in os.walk(source_dir):
                for f in files:
                    if f == 'mimetype': continue
                    full_path = os.path.join(root, f)
                    arc_name = os.path.relpath(full_path, source_dir)
                    zf.write(full_path, arc_name)

    async def _run_interactive_patch_loop(self, epub_path: str, config: TranslatorConfig, target_lang: str, auto_approve: bool = False):
        """交互式质检与修复闭环"""
        if not EPUBTranslationChecker:
            logger.warning("未找到 check_untranslated.py，跳过质检环节。")
            return

        checker = EPUBTranslationChecker()
        round_count = 1
        MAX_PATCH_ROUNDS = 5  # [新增] 最大修复轮次，防止死循环
        
        while True:
            # [新增] 检查是否达到最大轮次
            if round_count > MAX_PATCH_ROUNDS:
                print(f"\n⚠️  已达到最大修复轮次 ({MAX_PATCH_ROUNDS})，停止自动修复。")
                print("💡 剩余漏译可能是误判或需要人工处理。")
                break
            
            print(f"\n🔍 [第 {round_count} 轮质检] 正在扫描漏译段落...")
            try:
                # 捕获检查过程中的 print，只显示结果
                report = checker.check_epub(epub_path)
                untranslated_count = report['untranslated_count']
                
                if untranslated_count == 0:
                    print("\n🎉 完美！检测结果显示没有漏译。")
                    break
                
                print(f"\n⚠️  发现 {untranslated_count} 处疑似漏译，涉及 {len(set(i['file'] for i in report['details']))} 个文件")
                
                if auto_approve:
                    print("🤖 [自动模式] 已检测到漏译，自动开始修复...")
                    choice = 'y'
                else:
                    # 打印前3个示例
                    for i, item in enumerate(report['details'][:3]):
                        print(f"   - [{item['tag']}] {item['text'][:60]}...")
                    if len(report['details']) > 3:
                        print(f"   ... 等共 {untranslated_count} 处")
                    choice = input("\n👉 是否对这些漏译进行【强制修复】(y/n)? [默认为y]: ").strip().lower()
                
                if choice == 'n':
                    print("用户选择结束流程。")
                    break
                
                # 开始修复
                print(f"\n💉 [修复模式] 正在启动...")
                files_to_fix = set(item['file'] for item in report['details'])
                
                # [修复] 使用 dataclasses.replace 创建副本，避免污染原始 config
                from dataclasses import replace
                patch_config = replace(config, max_concurrent=50)
                
                async with self._create_translator(patch_config) as patch_translator:
                    patch_processor = HTMLProcessor(patch_translator)
                    
                    # [修复] 临时禁用过滤器 (Monkey Patch) - 包括 URL 过滤和中文检测
                    original_url_filter = patch_processor._is_url_or_code
                    original_chinese_filter = patch_processor._is_chinese_text
                    patch_processor._is_url_or_code = lambda text: False 
                    patch_processor._is_chinese_text = lambda text: False  # [新增] 强制翻译所有内容
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # 1. 解压
                        with zipfile.ZipFile(epub_path, 'r') as zf:
                            zf.extractall(temp_dir)
                        
                        # 2. 修复 (带进度条)
                        total_files = len(files_to_fix)
                        completed = [0]  # 使用列表以便在闭包中修改
                        
                        async def process_with_progress(rel_path: str):
                            full_path = os.path.join(temp_dir, rel_path)
                            if os.path.exists(full_path):
                                logger.info(f"   正在修补: {rel_path}")
                                await patch_processor.process_file(full_path, full_path, target_lang=target_lang)
                            completed[0] += 1
                            # 实时进度条
                            progress = completed[0] / total_files
                            bar_length = 30
                            block = int(round(bar_length * progress))
                            sys.stdout.write(f"\r修复进度: [{'#' * block}{'-' * (bar_length - block)}] {progress * 100:.1f}% ({completed[0]}/{total_files})")
                            sys.stdout.flush()
                        
                        tasks = [process_with_progress(rel_path) for rel_path in files_to_fix]
                        await asyncio.gather(*tasks)
                        print()  # 进度条结束后换行
                        
                        # 3. 打包
                        self._repack_epub(temp_dir, epub_path)
                    
                    # 恢复过滤器
                    patch_processor._is_url_or_code = original_url_filter
                    patch_processor._is_chinese_text = original_chinese_filter
                    
                    print(f"✅ 修复完成，已更新文件: {epub_path}")
                    self._print_stats(patch_translator)
                
                round_count += 1
                
            except Exception as e:
                logger.error(f"质检循环发生错误: {e}")
                import traceback
                traceback.print_exc()
                break

    async def _process_single_epub(self, input_path: str, output_path: str, config: TranslatorConfig, args):
        """处理单本 ePub 的核心逻辑 (包含翻译+质检)"""
        print(f"\n📘 正在处理: {os.path.basename(input_path)}")
        print(f"   输出至: {output_path}")
        
        # 1. 检查是否存在，决定是否跳过第一阶段
        skip_main = False
        if os.path.exists(output_path):
            if args.auto_approve:
                print(f"⏩ 输出文件已存在，自动跳过全量翻译，进入质检...")
                skip_main = True
            else:
                choice = input(f"\n📂 输出文件已存在。\n👉 是否跳过全量翻译，直接进入【质检与修复】? (y/n): ").strip().lower()
                if choice == 'y':
                    skip_main = True

        # 2. 全量翻译阶段
        if not skip_main:
            def progress_callback(progress: float, message: str):
                bar_length = 30
                block = int(round(bar_length * progress))
                sys.stdout.write(f"\r进度: [{'#' * block}{'-' * (bar_length - block)}] {progress * 100:.1f}% - {message}")
                sys.stdout.flush()

            async with self._create_translator(config) as translator:
                processor = EpubProcessor(translator)
                try:
                    await processor.translate_epub(
                        input_path=input_path,
                        output_path=output_path,
                        source_lang=args.source_lang,
                        target_lang=args.target_lang,
                        progress_callback=progress_callback
                    )
                    print("\n")
                    self._print_stats(translator)
                except Exception as e:
                    print("\n")
                    logger.error(f"ePub翻译中断: {e}")
                    self._print_stats(translator)
                    if not os.path.exists(output_path):
                        return

        # 3. 质检与修复阶段
        if os.path.exists(output_path):
            await self._run_interactive_patch_loop(output_path, config, args.target_lang, auto_approve=args.auto_approve)

    async def _handle_epub_command(self, args):
        config = self._get_config(args)
        
        if config.models:
            print(f"🚀 模型池已加载: {len(config.models)} 个模型")
            print(f"   首选: {config.models[0]}")

        input_path = Path(args.file)
        
        # --- 场景 A: 单文件 ---
        if input_path.is_file():
            # 确定输出路径
            if args.output:
                out_p = Path(args.output)
                if out_p.is_dir():
                    output_path = out_p / f"{input_path.stem}_translated{input_path.suffix}"
                else:
                    output_path = out_p
            else:
                output_path = input_path.with_name(f"{input_path.stem}_translated{input_path.suffix}")
            
            await self._process_single_epub(str(input_path), str(output_path), config, args)

        # --- 场景 B: 文件夹 (批量) - 新流程 ---
        elif input_path.is_dir():
            epub_files = list(input_path.glob("*.epub"))
            # 排除已翻译文件
            epub_files = [f for f in epub_files if "_translated" not in f.name and "间奏曲" not in f.name]
            
            if not epub_files:
                logger.error(f"在 {input_path} 中未找到 .epub 文件")
                return

            print(f"\n📚 发现 {len(epub_files)} 本电子书")
            print("=" * 60)
            print("📋 批量处理流程:")
            print("   阶段1: 全量翻译所有书籍")
            print("   阶段2: 统一质检与修复")
            print("   阶段3: 生成漏译报告")
            print("=" * 60)
            
            if args.output:
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = input_path 
            
            # ========== 阶段1: 全量翻译 ==========
            print(f"\n{'='*60}")
            print("📖 [阶段1] 全量翻译")
            print(f"{'='*60}")
            
            translated_files = []  # 收集已翻译的文件
            
            for idx, file in enumerate(epub_files, 1):
                print(f"\n📦 [{idx}/{len(epub_files)}] {file.name}")
                
                output_filename = f"{file.stem}_translated{file.suffix}"
                output_path = output_dir / output_filename
                
                try:
                    await self._translate_epub_only(str(file), str(output_path), config, args)
                    if output_path.exists():
                        translated_files.append(output_path)
                except Exception as e:
                    logger.error(f"翻译 {file.name} 失败: {e}")
                    continue
            
            print(f"\n✅ 阶段1完成: {len(translated_files)}/{len(epub_files)} 本书已翻译")
            
            # ========== 阶段2: 统一质检与修复 ==========
            if translated_files and EPUBTranslationChecker:
                print(f"\n{'='*60}")
                print("🔍 [阶段2] 统一质检与修复")
                print(f"{'='*60}")
                
                final_report = await self._batch_patch_all(translated_files, config, args.target_lang)
                
                # ========== 阶段3: 生成报告 ==========
                if final_report:
                    self._generate_final_report(final_report, output_dir)
            else:
                print("\n⏭️  跳过质检阶段 (无已翻译文件或缺少质检工具)")
                
        else:
            logger.error(f"输入路径不存在: {args.file}")
            sys.exit(1)
    
    async def _translate_epub_only(self, input_path: str, output_path: str, config: TranslatorConfig, args):
        """仅执行翻译，不进行质检（用于批量处理阶段1）"""
        print(f"   输出至: {output_path}")
        
        # 检查是否已存在
        if os.path.exists(output_path):
            print(f"   ⏩ 输出文件已存在，跳过翻译")
            return
        
        def progress_callback(progress: float, message: str):
            bar_length = 30
            block = int(round(bar_length * progress))
            sys.stdout.write(f"\r   进度: [{'#' * block}{'-' * (bar_length - block)}] {progress * 100:.1f}% - {message}")
            sys.stdout.flush()

        async with self._create_translator(config) as translator:
            processor = EpubProcessor(translator)
            try:
                await processor.translate_epub(
                    input_path=input_path,
                    output_path=output_path,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang,
                    progress_callback=progress_callback
                )
                print("\n")
                self._print_stats(translator)
            except Exception as e:
                print("\n")
                logger.error(f"ePub翻译中断: {e}")
                self._print_stats(translator)
    
    async def _batch_patch_all(self, epub_files: List[Path], config: TranslatorConfig, target_lang: str) -> Dict:
        """统一对所有已翻译文件进行质检和修复"""
        MAX_PATCH_ROUNDS = 3  # 批量模式下减少修复轮次
        checker = EPUBTranslationChecker()
        
        # 收集所有漏译报告
        all_reports = {}  # {文件路径: 最终漏译详情}
        
        for round_count in range(1, MAX_PATCH_ROUNDS + 1):
            print(f"\n🔄 [修复轮次 {round_count}/{MAX_PATCH_ROUNDS}]")
            
            files_need_fix = []  # 本轮需要修复的文件
            
            # 扫描所有文件
            for epub_path in epub_files:
                try:
                    report = checker.check_epub(str(epub_path))
                    if report['untranslated_count'] > 0:
                        files_need_fix.append((epub_path, report))
                        print(f"   ⚠️  {epub_path.name}: {report['untranslated_count']} 处漏译")
                    else:
                        print(f"   ✅ {epub_path.name}: 无漏译")
                except Exception as e:
                    logger.warning(f"检查 {epub_path.name} 失败: {e}")
            
            if not files_need_fix:
                print("\n🎉 所有文件均无漏译!")
                break
            
            print(f"\n   📝 本轮需修复: {len(files_need_fix)} 个文件")
            
            # 批量修复
            from dataclasses import replace
            patch_config = replace(config, max_concurrent=50)
            
            async with self._create_translator(patch_config) as patch_translator:
                for epub_path, report in files_need_fix:
                    try:
                        await self._patch_single_epub(epub_path, report, patch_translator, target_lang)
                    except Exception as e:
                        logger.error(f"修复 {epub_path.name} 失败: {e}")
                
                self._print_stats(patch_translator)
        
        # 最终扫描，收集剩余漏译
        print(f"\n📋 最终检查...")
        for epub_path in epub_files:
            try:
                report = checker.check_epub(str(epub_path))
                if report['untranslated_count'] > 0:
                    all_reports[str(epub_path)] = report['details']
                    print(f"   ⚠️  {epub_path.name}: 仍有 {report['untranslated_count']} 处漏译")
                else:
                    print(f"   ✅ {epub_path.name}: 完美")
            except Exception as e:
                logger.warning(f"最终检查 {epub_path.name} 失败: {e}")
        
        return all_reports
    
    async def _patch_single_epub(self, epub_path: Path, report: Dict, translator, target_lang: str):
        """修复单个 epub 文件的漏译"""
        files_to_fix = set(item['file'] for item in report['details'])
        
        patch_processor = HTMLProcessor(translator)
        # 禁用过滤器
        patch_processor._is_url_or_code = lambda text: False
        patch_processor._is_chinese_text = lambda text: False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(str(epub_path), 'r') as zf:
                zf.extractall(temp_dir)
            
            tasks = []
            for rel_path in files_to_fix:
                full_path = os.path.join(temp_dir, rel_path)
                if os.path.exists(full_path):
                    tasks.append(patch_processor.process_file(full_path, full_path, target_lang=target_lang))
            
            await asyncio.gather(*tasks)
            self._repack_epub(temp_dir, str(epub_path))
        
        print(f"   ✅ 已修复: {epub_path.name}")
    
    def _generate_final_report(self, reports: Dict, output_dir: Path):
        """生成最终漏译报告 (含人工翻译用的 JSON)"""
        import json
        from datetime import datetime
        
        if not reports:
            print("\n🎉 太棒了！所有文件均已完美翻译，无需人工处理。")
            return
        
        report_path = output_dir / "漏译报告.txt"
        json_path = output_dir / "人工翻译.json"
        
        total_issues = sum(len(details) for details in reports.values())
        
        # ========== 1. 生成 TXT 报告 (人类可读) ==========
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("📋 ePub 批量翻译 - 漏译报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"共 {len(reports)} 个文件存在漏译，总计 {total_issues} 处\n\n")
            f.write("💡 人工翻译方法:\n")
            f.write("   1. 打开同目录下的 '人工翻译.json'\n")
            f.write("   2. 在每个条目的 'translation' 字段填入您的译文\n")
            f.write("   3. 运行: python3 main.py apply-fix --json 人工翻译.json\n")
            f.write("=" * 60 + "\n\n")
            
            for epub_path, details in reports.items():
                f.write("-" * 40 + "\n")
                f.write(f"📖 {Path(epub_path).name}\n")
                f.write(f"   漏译数: {len(details)}\n\n")
                
                # 按文件分组
                by_file = {}
                for item in details:
                    file_name = item['file']
                    if file_name not in by_file:
                        by_file[file_name] = []
                    by_file[file_name].append(item)
                
                for file_name, items in by_file.items():
                    f.write(f"   📄 {file_name}:\n")
                    for item in items[:10]:
                        text_preview = item['text'][:80].replace('\n', ' ')
                        f.write(f"      [{item['tag']}] {text_preview}...\n")
                    if len(items) > 10:
                        f.write(f"      ... 等 {len(items)} 处\n")
                    f.write("\n")
        
        # ========== 2. 生成人工翻译用的 JSON ==========
        # 结构设计: 以 epub 文件为单位，每个条目包含原文和空的译文字段
        json_data = {
            "_说明": "请在每个条目的 'translation' 字段填入您的译文，然后运行 apply-fix 命令",
            "_命令示例": f"python3 main.py apply-fix --json \"{json_path}\"",
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_issues": total_issues,
            "books": []
        }
        
        for epub_path, details in reports.items():
            book_entry = {
                "epub_file": str(epub_path),
                "epub_name": Path(epub_path).name,
                "segments": []
            }
            
            for idx, item in enumerate(details):
                segment = {
                    "id": idx + 1,
                    "html_file": item['file'],
                    "tag": item['tag'],
                    "original": item.get('full_text', item['text']),  # 完整原文
                    "translation": ""  # <-- 用户在这里填写译文
                }
                book_entry["segments"].append(segment)
            
            json_data["books"].append(book_entry)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # ========== 3. 打印提示 ==========
        print(f"\n{'='*60}")
        print(f"📋 [阶段3] 漏译报告已生成")
        print(f"{'='*60}")
        print(f"   📄 可读报告: {report_path}")
        print(f"   📝 人工翻译: {json_path}")
        print(f"   涉及: {len(reports)} 本书，共 {total_issues} 处漏译")
        print(f"\n💡 人工翻译流程:")
        print(f"   1. 打开 '{json_path.name}'")
        print(f"   2. 在每个条目的 \"translation\" 字段填入您的译文")
        print(f"   3. 运行: python3 main.py apply-fix --json \"{json_path}\"")
        print(f"{'='*60}")

    async def _handle_json_command(self, args):
        logger.info(f"开始JSON翻译: {args.file}")
        config = self._get_config(args)
        async with self._create_translator(config) as translator:
            processor = JSONProcessor(translator)
            try:
                result = await processor.translate_file(args.file, args.output, args.source_lang, args.target_lang)
                logger.info(f"JSON翻译完成! 进度: {result.get('progress', 0)}%")
                self._print_stats(translator)
            except Exception as e:
                logger.error(f"JSON翻译失败: {e}")
                sys.exit(1)

    async def _handle_html_command(self, args):
        logger.info(f"开始HTML翻译: {args.file}")
        config = self._get_config(args)
        async with self._create_translator(config) as translator:
            processor = HTMLProcessor(translator)
            try:
                result = await processor.process_file(args.file, args.output, args.source_lang, args.target_lang)
                logger.info(f"HTML翻译完成! 已翻译文本块: {result.get('translated_count', 0)}")
                self._print_stats(translator)
            except Exception as e:
                logger.error(f"HTML翻译失败: {e}")
                sys.exit(1)

    def _handle_server_command(self, args):
        run_server(host=args.host, port=args.port, api_key=args.api_key, debug=args.debug)

    def _handle_applyfix_command(self, args):
        """读取人工翻译 JSON 并回填到 ePub"""
        import json
        from bs4 import BeautifulSoup
        
        json_path = Path(args.json)
        if not json_path.exists():
            logger.error(f"找不到 JSON 文件: {json_path}")
            sys.exit(1)
        
        print(f"\n📖 读取人工翻译文件: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        books = data.get('books', [])
        if not books:
            print("⚠️  JSON 中没有需要处理的内容")
            return
        
        total_applied = 0
        total_skipped = 0
        
        for book in books:
            epub_path = Path(book['epub_file'])
            if not epub_path.exists():
                logger.warning(f"⚠️  跳过 (文件不存在): {epub_path}")
                continue
            
            segments = book.get('segments', [])
            # 过滤出有译文的条目
            segments_with_trans = [s for s in segments if s.get('translation', '').strip()]
            
            if not segments_with_trans:
                print(f"⏭️  {book['epub_name']}: 无需回填 (没有填写译文)")
                continue
            
            print(f"\n📘 处理: {book['epub_name']} ({len(segments_with_trans)} 处译文)")
            
            # 按 html_file 分组
            by_file = {}
            for seg in segments_with_trans:
                html_file = seg['html_file']
                if html_file not in by_file:
                    by_file[html_file] = []
                by_file[html_file].append(seg)
            
            # 解压 -> 修改 -> 打包
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(epub_path, 'r') as zf:
                    zf.extractall(temp_dir)
                
                for html_file, segs in by_file.items():
                    full_path = os.path.join(temp_dir, html_file)
                    if not os.path.exists(full_path):
                        logger.warning(f"   文件不存在: {html_file}")
                        continue
                    
                    # 读取并解析 HTML
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    soup = BeautifulSoup(content, 'html.parser')
                    modified = False
                    
                    for seg in segs:
                        original = seg['original']
                        translation = seg['translation']
                        tag_name = seg['tag']
                        
                        # 查找匹配的元素
                        for elem in soup.find_all(tag_name):
                            elem_text = elem.get_text(" ", strip=True)
                            # 精确匹配或包含匹配
                            if elem_text == original or original in elem_text:
                                # 替换文本内容
                                elem.clear()
                                elem.append(translation)
                                modified = True
                                total_applied += 1
                                logger.info(f"   ✅ 已替换: {original[:30]}... → {translation[:30]}...")
                                break
                        else:
                            total_skipped += 1
                            logger.warning(f"   ⚠️  未找到匹配: {original[:50]}...")
                    
                    if modified:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(str(soup))
                
                # 重新打包
                self._repack_epub(temp_dir, str(epub_path))
                print(f"   ✅ 已更新: {epub_path}")
        
        print(f"\n{'='*60}")
        print(f"📊 回填完成!")
        print(f"   ✅ 成功替换: {total_applied} 处")
        print(f"   ⚠️  未找到匹配: {total_skipped} 处")
        print(f"{'='*60}")

    def _handle_genjson_command(self, args):
        """扫描已翻译的 EPUB 目录，生成人工翻译 JSON"""
        import json
        from datetime import datetime
        
        if not EPUBTranslationChecker:
            logger.error("缺少 check_untranslated.py，无法执行质检")
            sys.exit(1)
        
        target_dir = Path(args.dir)
        if not target_dir.exists():
            logger.error(f"目录不存在: {target_dir}")
            sys.exit(1)
        
        # 查找所有已翻译的 EPUB
        epub_files = list(target_dir.glob("*_translated.epub"))
        if not epub_files:
            print(f"⚠️  在 {target_dir} 中没有找到 *_translated.epub 文件")
            return
        
        print(f"\n🔍 扫描目录: {target_dir}")
        print(f"   发现 {len(epub_files)} 个已翻译 EPUB")
        print("="*60)
        
        checker = EPUBTranslationChecker()
        all_reports = {}
        
        for epub_path in epub_files:
            try:
                report = checker.check_epub(str(epub_path))
                if report['untranslated_count'] > 0:
                    all_reports[str(epub_path)] = report['details']
                    print(f"   ⚠️  {epub_path.name}: {report['untranslated_count']} 处漏译")
                else:
                    print(f"   ✅ {epub_path.name}: 无漏译")
            except Exception as e:
                logger.warning(f"检查 {epub_path.name} 失败: {e}")
        
        if not all_reports:
            print("\n🎉 所有文件均无漏译，无需生成 JSON")
            return
        
        # 调用现有的报告生成方法
        self._generate_final_report(all_reports, target_dir)

    def run(self):
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            return 0
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        try:
            if args.command == "json": asyncio.run(self._handle_json_command(args))
            elif args.command == "html": asyncio.run(self._handle_html_command(args))
            elif args.command == "epub": asyncio.run(self._handle_epub_command(args))
            elif args.command == "server": self._handle_server_command(args)
            elif args.command == "apply-fix": self._handle_applyfix_command(args)
            elif args.command == "generate-json": self._handle_genjson_command(args)
        except KeyboardInterrupt:
            print("\n⚠️ 任务被用户中断")
        except Exception as e:
            logger.critical(f"发生未处理的异常: {e}", exc_info=True)
            return 1
        return 0

if __name__ == "__main__":
    cli = MainCLI()
    sys.exit(cli.run())