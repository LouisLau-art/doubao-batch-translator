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
from typing import Optional

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
        
        # 全局并发控制参数 (移动到父级，让所有子命令都能用)
        parser.add_argument("--max-concurrent", type=int, help="最大并发请求数 (默认: 20)")
        parser.add_argument("--max-rps", type=float, help="每秒最大请求数 (默认: 10.0)")
        
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
        epub_parser.add_argument("--file", "-f", required=True, help="输入文件")
        epub_parser.add_argument("--output", "-o", required=True, help="输出文件")
        epub_parser.add_argument("--source-lang", help="源语言")
        epub_parser.add_argument("--target-lang", "-t", default="zh", help="目标语言")
        
        # Server命令
        server_parser = subparsers.add_parser("server", help="启动HTTP API服务器")
        server_parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
        server_parser.add_argument("--port", "-p", type=int, default=8000, help="监听端口")
        server_parser.add_argument("--debug", action="store_true", help="启用调试模式")
        
        return parser
    
    def _get_config(self, args) -> TranslatorConfig:
        """获取配置对象"""
        config_kwargs = {}
        
        # 优先使用命令行参数，其次读取环境变量
        if args.api_key:
            api_key = args.api_key
        else:
            api_key = os.getenv("ARK_API_KEY")
            
        if not api_key:
            logger.error("未找到API密钥！请设置ARK_API_KEY环境变量或使用--api-key参数。")
            sys.exit(1)

        # 传递并发配置
        if args.max_concurrent:
            config_kwargs['max_concurrent'] = args.max_concurrent
        if args.max_rps:
            config_kwargs['max_requests_per_second'] = args.max_rps
            
        return TranslatorConfig(api_key=api_key, **config_kwargs)
    
    def _create_translator(self, config: TranslatorConfig) -> AsyncTranslator:
        """工厂方法：创建并配置翻译器实例"""
        # 注意：这里假设 AsyncTranslator (client.py) 已经更新支持接收 max_concurrent 参数
        # 如果 client.py 还没改，这些参数会被忽略，但不会报错
        translator = AsyncTranslator(config.api_key)
        
        # [补丁] 如果 client.py 的 __init__ 没支持参数，我们在实例上强行修改
        # 这是一个临时的 Monkey Patch，为了确保你的 CLI 参数生效
        if hasattr(config, 'max_concurrent') and config.max_concurrent:
            if hasattr(translator.client, 'semaphore'):
                 translator.client.semaphore = asyncio.Semaphore(config.max_concurrent)
                 logger.info(f"并发数已设置为: {config.max_concurrent}")
                 
        return translator

    async def _handle_json_command(self, args):
        logger.info(f"开始JSON翻译: {args.file}")
        config = self._get_config(args)
        
        # [优化] 使用 async with 统一管理生命周期
        async with self._create_translator(config) as translator:
            processor = JSONProcessor(translator)
            try:
                result = await processor.translate_file(
                    input_file=args.file,
                    output_file=args.output,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang
                )
                logger.info(f"JSON翻译完成! 进度: {result.get('progress', 0)}%")
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
                    source_lang=args.source_lang,
                    target_lang=args.target_lang
                )
                logger.info(f"HTML翻译完成! 已翻译文本块: {result.get('translated_count', 0)}")
            except Exception as e:
                logger.error(f"HTML翻译失败: {e}")
                sys.exit(1)

    async def _handle_epub_command(self, args):
        logger.info(f"开始ePub翻译: {args.file}")
        config = self._get_config(args)
        
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
                print() # 进度条完成后换行
                logger.info(f"ePub翻译成功! 输出: {args.output}")
            except Exception as e:
                print() # 异常时也要换行，防止日志混乱
                logger.error(f"ePub翻译失败: {e}")
                sys.exit(1)

    def _handle_server_command(self, args):
        logger.info("正在启动 HTTP API 服务器...")
        # 这里的实现逻辑通常在 server/api.py 里，保持原样即可
        # 只要确保 args 参数能传进去
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