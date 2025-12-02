#!/usr/bin/env python3
"""
豆包翻译模型统一接口 - 核心模块
提供异步翻译、批处理、并发控制等功能
"""

from .config import (
    TranslatorConfig, 
    SUPPORTED_LANGUAGES,
    validate_language_code,
    get_language_name,
    format_api_request
)
from .exceptions import *
from .translator import AsyncTranslator

__version__ = "2.0.0"
__all__ = [
    "TranslatorConfig",
    "SUPPORTED_LANGUAGES", 
    "validate_language_code",
    "get_language_name",
    "format_api_request",
    "AsyncTranslator",
    # 异常类
    "TranslatorError",
    "APIError",
    "RateLimitError",
    "AuthenticationError",
    "ConfigurationError",
    "ValidationError", 
    "FileProcessingError",
    "BatchProcessingError",
    "NetworkError",
    "TimeoutError",
    "UnsupportedLanguageError"
]