#!/usr/bin/env python3
"""
豆包翻译模型统一接口 - 主入口
支持CLI命令行工具和HTTP Server服务
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from core import TranslatorConfig, AsyncTranslator
from processors import JSONProcessor, HTMLProcessor
from server import DoubaoServer, run_server


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
        """初始化CLI"""
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建参数解析器"""
        parser = argparse.ArgumentParser(
            description="豆包翻译模型统一接口 - 支持JSON、HTML翻译和HTTP API服务",
            epilog="""
使用示例:
  # JSON翻译
  python main.py json --file translation_work.json --target-lang zh
  
  # HTML翻译  
  python main.py html --file input.html --target-lang zh
  
  # 启动HTTP服务器
  python main.py server --port 8000
  
  # 自定义配置
  python main.py json --file data.json --api-key YOUR_KEY --concurrent 3 --rps 30
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # 通用参数
        parser.add_argument("--api-key", help="豆包API密钥（也可以通过ARK_API_KEY环境变量设置）")
        parser.add_argument("--verbose", "-v", action="store_true", help="启用详细日志")
        parser.add_argument("--config-file", help="配置文件路径（暂未实现）")
        
        # 子命令
        subparsers = parser.add_subparsers(dest="command", help="可用命令")
        
        # JSON翻译命令
        json_parser = subparsers.add_parser("json", help="JSON文件翻译（RenPy翻译专用）")
        json_parser.add_argument("--file", "-f", required=True, help="输入JSON文件路径")
        json_parser.add_argument("--output", "-o", help="输出JSON文件路径（默认覆盖原文件）")
        json_parser.add_argument("--source-lang", help="源语言代码（可选，自动检测）")
        json_parser.add_argument("--target-lang", "-t", default="zh", help="目标语言代码（默认：zh）")
        
        # HTML翻译命令
        html_parser = subparsers.add_parser("html", help="HTML文件翻译")
        html_parser.add_argument("--file", "-f", required=True, help="输入HTML文件路径")
        html_parser.add_argument("--output", "-o", help="输出HTML文件路径（默认覆盖原文件）")
        html_parser.add_argument("--source-lang", help="源语言代码（可选，自动检测）")
        html_parser.add_argument("--target-lang", "-t", default="zh", help="目标语言代码（默认：zh）")
        
        # HTTP服务器命令
        server_parser = subparsers.add_parser("server", help="启动HTTP API服务器")
        server_parser.add_argument("--host", default="0.0.0.0", help="绑定地址（默认：0.0.0.0）")
        server_parser.add_argument("--port", "-p", type=int, default=8000, help="监听端口（默认：8000）")
        server_parser.add_argument("--debug", action="store_true", help="启用调试模式")
        
        # 服务器高级选项
        server_group = server_parser.add_argument_group("高级选项")
        server_group.add_argument("--max-concurrent", type=int, help="最大并发数")
        server_group.add_argument("--max-rps", type=float, help="每秒最大请求数")
        
        return parser
    
    def _get_config(self, args) -> TranslatorConfig:
        """获取翻译器配置
        
        Args:
            args: 命令行参数
            
        Returns:
            翻译器配置
        """
        config_kwargs = {}
        
        # 设置并发控制参数
        if hasattr(args, 'max_concurrent') and args.max_concurrent:
            config_kwargs['max_concurrent'] = args.max_concurrent
        
        if hasattr(args, 'max_rps') and args.max_rps:
            config_kwargs['max_requests_per_second'] = args.max_rps
        
        try:
            if args.api_key:
                return TranslatorConfig(api_key=args.api_key, **config_kwargs)
            else:
                return TranslatorConfig.from_env(**config_kwargs)
        except Exception as e:
            logger.error(f"配置错误: {e}")
            sys.exit(1)
    
    def _setup_logging(self, verbose: bool = False):
        """设置日志级别
        
        Args:
            verbose: 是否启用详细日志
        """
        level = logging.DEBUG if verbose else logging.INFO
        logging.getLogger().setLevel(level)
        
        if verbose:
            logger.debug("已启用详细日志模式")
    
    async def _handle_json_command(self, args):
        """处理JSON翻译命令
        
        Args:
            args: 命令行参数
        """
        logger.info("开始JSON文件翻译...")
        
        try:
            # 获取配置
            config = self._get_config(args)
            
            # 创建翻译器和处理器
            async with AsyncTranslator(config) as translator:
                processor = JSONProcessor(translator)
                
                # 执行翻译
                result = await processor.translate_file(
                    input_file=args.file,
                    output_file=args.output,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang
                )
                
                # 输出结果
                print(f"翻译完成!")
                print(f"总计: {result['total']} 条目")
                print(f"已完成: {result['translated']} 条目")
                print(f"进度: {result['progress']}%")
                
                if result.get('success'):
                    logger.info(f"结果已保存到: {result.get('output_file', args.output or args.file)}")
                else:
                    logger.error("翻译过程中遇到错误")
                    sys.exit(1)
                    
        except Exception as e:
            logger.error(f"JSON翻译失败: {e}")
            sys.exit(1)
    
    async def _handle_html_command(self, args):
        """处理HTML翻译命令
        
        Args:
            args: 命令行参数
        """
        logger.info("开始HTML文件翻译...")
        
        try:
            # 获取配置
            config = self._get_config(args)
            
            # 创建翻译器和处理器
            async with AsyncTranslator(config) as translator:
                processor = HTMLProcessor(translator)
                
                # 执行翻译
                result = await processor.process_file(
                    input_file=args.file,
                    output_file=args.output,
                    source_lang=args.source_lang,
                    target_lang=args.target_lang
                )
                
                # 输出结果
                print(f"翻译完成!")
                print(f"原始文本: {result['original_text_count']} 个")
                print(f"成功翻译: {result['translated_count']} 个")
                print(f"跳过文本: {result['skipped_count']} 个")
                
                if result.get('success'):
                    logger.info(f"结果已保存到: {result.get('output_file', args.output or args.file)}")
                else:
                    logger.error("翻译过程中遇到错误")
                    sys.exit(1)
                    
        except Exception as e:
            logger.error(f"HTML翻译失败: {e}")
            sys.exit(1)
    
    def _handle_server_command(self, args):
        """处理HTTP服务器命令
        
        Args:
            args: 命令行参数
        """
        logger.info("启动HTTP API服务器...")
        
        try:
            # 获取API密钥
            if not args.api_key:
                import os
                args.api_key = os.getenv("ARK_API_KEY")
                if not args.api_key:
                    logger.error("未提供API密钥，请设置ARK_API_KEY环境变量或使用--api-key参数")
                    sys.exit(1)
            
            # 构建配置参数
            config_kwargs = {}
            if hasattr(args, 'max_concurrent') and args.max_concurrent:
                config_kwargs['max_concurrent'] = args.max_concurrent
            
            if hasattr(args, 'max_rps') and args.max_rps:
                config_kwargs['max_requests_per_second'] = args.max_rps
            
            # 启动服务器
            run_server(
                host=args.host,
                port=args.port,
                api_key=args.api_key,
                debug=args.debug
            )
            
        except KeyboardInterrupt:
            logger.info("服务器已停止")
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            sys.exit(1)
    
    def run(self, args: list = None) -> int:
        """运行CLI
        
        Args:
            args: 命令行参数列表
            
        Returns:
            退出码（0表示成功）
        """
        try:
            # 解析参数
            parsed_args = self.parser.parse_args(args)
            
            # 如果没有指定命令，显示帮助
            if not parsed_args.command:
                self.parser.print_help()
                return 0
            
            # 设置日志
            self._setup_logging(parsed_args.verbose)
            
            # 根据命令类型执行相应逻辑
            if parsed_args.command == "json":
                return asyncio.run(self._handle_json_command(parsed_args))
            elif parsed_args.command == "html":
                return asyncio.run(self._handle_html_command(parsed_args))
            elif parsed_args.command == "server":
                self._handle_server_command(parsed_args)
                return 0
            else:
                logger.error(f"未知命令: {parsed_args.command}")
                return 1
                
        except KeyboardInterrupt:
            logger.info("用户中断操作")
            return 0
        except Exception as e:
            logger.error(f"执行过程中发生错误: {e}")
            return 1


def main():
    """主函数"""
    cli = MainCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()