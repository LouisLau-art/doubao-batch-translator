#!/usr/bin/env python3
"""
处理器模块
提供不同类型的文件翻译处理器
"""

from .json_worker import JSONProcessor
from .html_worker import HTMLProcessor
from .epub_worker import EpubProcessor

__all__ = [
    "JSONProcessor", 
    "HTMLProcessor",
    "EpubProcessor"
]