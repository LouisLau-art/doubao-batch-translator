#!/usr/bin/env python3
"""
豆包翻译模型统一接口 - 主入口
支持CLI命令行工具和HTTP Server服务
"""

import argparse
import asyncio
import logging
import sys
import os
from typing import Optional, Dict

# 确保能找到 core 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import TranslatorConfig
from core.client import AsyncTranslator
from processors.json_worker import JSONProcessor
from processors.html_worker import HTMLProcessor
from processors.epub_worker import EpubProcessor
from server.api import run_server


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('doubao-translator.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

class MainCLI:
    """主命令行界面"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建参数解析器"""
        parser = argparse.ArgumentParser(
            description="豆包翻译模型统一接口 - 支持JSON、HTML、ePub翻译和HTTP API服务",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # 通用参数
        parser.add_argument("--api-key", help="豆包API密钥")
        parser.add_argument("--verbose", "-v", action="store_true", help="启用详细日志")
        
        # 全局并发控制参数
        parser.add_argument("--max-concurrent", type=int, help="最大并发请求数 (建议: 30)")
        parser.add_argument("--max-rps", type=float, help="每秒最大请求数 (建议: 20.0)")
        
        # 子命令
        subparsers = parser.add_subparsers(dest="command", help="可用命令")
        
        # JSON翻译命令
        json_parser = subparsers.add_parser("json", help="JSON文件翻译")
        json_parser.add_argument("--file", "-f", required=True, help="输入文件")
        json_parser.add_argument("--output", "-o", help="输出文件")
        json_parser.add_argument("--source-lang", help="源语言")
        json_parser.add_argument("--target-lang", "-t", default="en", help="目标语言 (默认: en)")
        
        # HTML翻译命令
        html_parser = subparsers.add_parser("html", help="HTML文件翻译")
        html_parser.add_argument("--file", "-f", required=True, help="输入文件")
        html_parser.add_argument("--output", "-o", help="输出文件")
        html_parser.add_argument("--source-lang", help="源语言")
        html_parser.add_argument("--target-lang", "-t", default="en", help="目标语言 (默认: en)")
        
        # ePub翻译命令
        epub_parser = subparsers.add_parser("epub", help="ePub电子书翻译")
        epub_parser.add_argument("--file", "-f", required=True, help="输入文件")
        epub_parser.add_argument("--output", "-o", required=True, help="输出文件")
        epub_parser.add_argument("--source-lang", help="源语言")
        epub_parser.add_argument("--target-lang", "-t", default="en", help="目标语言 (默认: en)")
        
        # Server命令
        server_parser = subparsers.add_parser("server", help="启动HTTP API服务器")
        server_parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
        server_parser.add_argument("--port", "-p", type=int, default=8000, help="监听端口")
        server_parser.add_argument("--debug", action="store_true", help="启用调试模式")
        
        return parser
    
    def _get_config(self, args) -> TranslatorConfig:
        """获取配置对象"""
        config_kwargs = {}
        
        # 传递并发配置
        if args.max_concurrent:
            config_kwargs['max_concurrent'] = args.max_concurrent
        if args.max_rps:
            config_kwargs['max_requests_per_second'] = args.max_rps
            
        # 使用 from_args，它会内部调用 from_env 并加载 models.json
        try:
            return TranslatorConfig.from_args(
                api_key=args.api_key, 
                **config_kwargs
            )
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            sys.exit(1)
    
    def _create_translator(self, config: TranslatorConfig) -> AsyncTranslator:
        """工厂方法：创建并配置翻译器实例"""
        # 直接传入 config 对象，确保 client.py 能读取到 config.models 和并发设置
        translator = AsyncTranslator(config)
        return translator

    def _print_stats(self, translator: AsyncTranslator):
        """打印模型使用统计 (含 Token)"""
        # 检查 translator 是否支持 get_stats (兼容性保护)
        if not hasattr(translator, 'get_stats'):
            return

        stats = translator.get_stats()
        
        # 计算总数
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
        
        # 按调用次数排序
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

    async def _handle_json_command(self, args):
        logger.info(f"开始JSON翻译: {args.file}")
        config = self._get_config(args)
        
        async with self._create_translator(config) as translator:
            processor = JSONProcessor(translator)
            try:
                result = await processor.translate_file(
                    input_file=args.file,
                    output_file=args.output,
                    source_lang=translator.config.source_language,
                    target_lang=translator.config.target_language
                )
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
                result = await processor.process_file(
                    input_file=args.file,
                    output_file=args.output,
                    source_lang=translator.config.source_language,
                    target_lang=translator.config.target_language
                )
                logger.info(f"HTML翻译完成! 已翻译文本块: {result.get('translated_count', 0)}")
                self._print_stats(translator)
            except Exception as e:
                logger.error(f"HTML翻译失败: {e}")
                sys.exit(1)

    async def _handle_epub_command(self, args):
        logger.info(f"开始ePub翻译: {args.file}")
        config = self._get_config(args)
        
        # 打印模型池信息，用于确认加载成功
        if config.models:
            print(f"🚀 模型池已加载: {len(config.models)} 个模型")
            print(f"   首选: {config.models[0]}")
            if len(config.models) > 1:
                print(f"   备用: {config.models[1]} 等...")
        else:
            print("⚠️ 警告: 未检测到模型池，将仅使用默认模型")

        def progress_callback(progress: float, message: str):
            # 使用 \r 实现单行刷新进度条
            bar_length = 30
            block = int(round(bar_length * progress))
            text = "\r进度: [{0}] {1:.1f}% - {2}".format(
                "#" * block + "-" * (bar_length - block), 
                progress * 100, 
                message
            )
            sys.stdout.write(text)
            sys.stdout.flush()

        async with self._create_translator(config) as translator:
            processor = EpubProcessor(translator)
            try:
                result = await processor.translate_epub(
                    input_path=args.file,
                    output_path=args.output,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang,
                    progress_callback=progress_callback
                )
                print() 
                logger.info(f"ePub翻译成功! 输出: {args.output}")
                
                # 打印统计表格
                self._print_stats(translator)
                
            except Exception as e:
                print() 
                logger.error(f"ePub翻译失败: {e}")
                # 即使失败也打印统计，查看消耗
                self._print_stats(translator)
                sys.exit(1)

    def _handle_server_command(self, args):
        logger.info("正在启动 HTTP API 服务器...")
        run_server(
            host=args.host,
            port=args.port,
            api_key=args.api_key or os.getenv("ARK_API_KEY"),
            debug=args.debug
        )

    def run(self):
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            return 0
        
        # 设置日志级别
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug模式已开启")

        try:
            if args.command == "json":
                asyncio.run(self._handle_json_command(args))
            elif args.command == "html":
                asyncio.run(self._handle_html_command(args))
            elif args.command == "epub":
                asyncio.run(self._handle_epub_command(args))
            elif args.command == "server":
                self._handle_server_command(args)
        except KeyboardInterrupt:
            print("\n")
            logger.warning("任务被用户中断")
            return 0
        except Exception as e:
            logger.critical(f"发生未处理的异常: {e}", exc_info=True)
            return 1
        return 0

if __name__ == "__main__":
    cli = MainCLI()
    sys.exit(cli.run())