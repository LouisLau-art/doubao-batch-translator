#!/usr/bin/env python3
"""
核心异常模块
定义翻译器相关的所有异常类
"""


class TranslatorError(Exception):
    """翻译器基础异常类"""
    pass


class APIError(TranslatorError):
    """API相关异常"""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RateLimitError(TranslatorError):
    """频率限制异常"""
    pass


class AuthenticationError(TranslatorError):
    """认证异常"""
    pass


class ConfigurationError(TranslatorError):
    """配置异常"""
    pass


class ValidationError(TranslatorError):
    """数据验证异常"""
    pass


class FileProcessingError(TranslatorError):
    """文件处理异常"""
    pass


class BatchProcessingError(TranslatorError):
    """批处理异常"""
    def __init__(self, message: str, batch_index: int = None, batch_items: list = None):
        super().__init__(message)
        self.batch_index = batch_index
        self.batch_items = batch_items


class NetworkError(TranslatorError):
    """网络相关异常"""
    pass


class TimeoutError(TranslatorError):
    """超时异常"""
    pass


class UnsupportedLanguageError(TranslatorError):
    """不支持的语言异常"""
    def __init__(self, language_code: str):
        self.language_code = language_code
        super().__init__(f"不支持的语言代码: {language_code}")