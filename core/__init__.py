#!/usr/bin/env python3
"""
Core module initialization
"""

# 导出配置相关
from .config import (
    TranslatorConfig,
    DOUBAO_TRANSLATION_URL,  # [新增]
    DOUBAO_CHAT_URL,         # [新增]
    SUPPORTED_LANGUAGES,
    validate_language_code,
    get_language_name,
    DOUBAO_API_KEY_ENV
)

# 导出客户端相关
from .client import (
    AsyncDoubaoClient,
    AsyncTranslator
)

# 导出异常相关
from .exceptions import (
    TranslatorError,
    ConfigurationError,
    APIError,
    RateLimitError,
    AuthenticationError,
    ValidationError,
    FileProcessingError
)

# 导出版本号
__version__ = "2.1.0"

# 定义导出的符号列表
__all__ = [
    # Config
    "TranslatorConfig",
    "DOUBAO_TRANSLATION_URL",
    "DOUBAO_CHAT_URL",
    "SUPPORTED_LANGUAGES",
    "validate_language_code",
    "get_language_name",
    "DOUBAO_API_KEY_ENV",
    
    # Client
    "AsyncDoubaoClient",
    "AsyncTranslator",
    
    # Exceptions
    "TranslatorError",
    "ConfigurationError",
    "APIError",
    "RateLimitError",
    "AuthenticationError",
    "ValidationError",
    "FileProcessingError"
]