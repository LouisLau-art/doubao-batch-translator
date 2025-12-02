#!/usr/bin/env python3
"""
核心配置模块
包含豆包API常量、配置管理和语言支持定义
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass


# 豆包API配置常量
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
DOUBAO_MODEL = "doubao-seed-translation-250915"
DOUBAO_API_KEY_ENV = "ARK_API_KEY"

# 默认配置
DEFAULT_MAX_CONCURRENT = 5
DEFAULT_MAX_REQUESTS_PER_SECOND = 50.0
DEFAULT_BATCH_SIZE = 15
DEFAULT_MAX_CHARS_PER_BATCH = 500
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    # 中文
    "zh": "中文（简体）",
    "zh-Hant": "中文（繁体）",
    
    # 欧美语言
    "en": "英语",
    "de": "德语", 
    "fr": "法语",
    "es": "西班牙语",
    "it": "意大利语",
    "pt": "葡萄牙语",
    "ru": "俄语",
    "pl": "波兰语",
    "nl": "荷兰语",
    "sv": "瑞典语",
    "da": "丹麦语",
    "fi": "芬兰语",
    "no": "挪威布克莫尔语",
    
    # 亚洲语言
    "ja": "日语",
    "ko": "韩语",
    "th": "泰语",
    "vi": "越南语",
    "id": "印尼语",
    "ms": "马来语",
    
    # 其他语言
    "ar": "阿拉伯语",
    "cs": "捷克语",
    "hr": "克罗地亚语",
    "hu": "匈牙利语",
    "ro": "罗马尼亚语",
    "tr": "土耳其语",
    "uk": "乌克兰语",
}


@dataclass
class TranslatorConfig:
    """翻译器配置类"""
    api_key: str
    api_url: str = DOUBAO_API_URL
    model: str = DOUBAO_MODEL
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    max_requests_per_second: float = DEFAULT_MAX_REQUESTS_PER_SECOND
    batch_size: int = DEFAULT_BATCH_SIZE
    max_chars_per_batch: int = DEFAULT_MAX_CHARS_PER_BATCH
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    
    def __post_init__(self):
        """验证配置参数"""
        if not self.api_key:
            raise ValueError("API密钥不能为空")
        
        if self.max_concurrent <= 0:
            raise ValueError("最大并发数必须大于0")
            
        if self.max_requests_per_second <= 0:
            raise ValueError("每秒最大请求数必须大于0")
            
        if self.timeout <= 0:
            raise ValueError("超时时间必须大于0")
            
        if self.max_retries < 0:
            raise ValueError("最大重试次数不能小于0")
    
    @classmethod
    def from_env(cls) -> 'TranslatorConfig':
        """从环境变量创建配置"""
        api_key = os.getenv(DOUBAO_API_KEY_ENV)
        if not api_key:
            raise ValueError(
                f"未找到API密钥。请设置{DOUBAO_API_KEY_ENV}环境变量或通过参数传入"
            )
        
        return cls(
            api_key=api_key,
            api_url=os.getenv('DOUBAO_API_URL', DOUBAO_API_URL),
            model=os.getenv('DOUBAO_MODEL', DOUBAO_MODEL),
            max_concurrent=int(os.getenv('MAX_CONCURRENT', str(DEFAULT_MAX_CONCURRENT))),
            max_requests_per_second=float(os.getenv('MAX_REQUESTS_PER_SECOND', str(DEFAULT_MAX_REQUESTS_PER_SECOND))),
            timeout=float(os.getenv('REQUEST_TIMEOUT', str(DEFAULT_TIMEOUT))),
            max_retries=int(os.getenv('MAX_RETRIES', str(DEFAULT_MAX_RETRIES))),
        )
    
    @classmethod 
    def from_args(cls, api_key: str, **kwargs) -> 'TranslatorConfig':
        """从参数创建配置"""
        config = cls.from_env() if not api_key else cls(api_key=api_key)
        
        # 更新配置参数
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config


def validate_language_code(lang_code: str) -> bool:
    """验证语言代码是否受支持"""
    return lang_code in SUPPORTED_LANGUAGES


def get_language_name(lang_code: str) -> Optional[str]:
    """获取语言代码对应的语言名称"""
    return SUPPORTED_LANGUAGES.get(lang_code)


def format_api_request(model: str, input_items: List[Dict], 
                      source_language: Optional[str] = None, 
                      target_language: Optional[str] = None) -> Dict:
    """格式化豆包API请求体
    
    Args:
        model: 模型名称
        input_items: 输入文本列表
        source_language: 源语言代码（可选）
        target_language: 目标语言代码（必选）
        
    Returns:
        格式化的请求体
    """
    if not target_language:
        raise ValueError("目标语言代码不能为空")
    
    # 验证目标语言
    if not validate_language_code(target_language):
        raise ValueError(f"不支持的目标语言: {target_language}")
    
    # 如果提供了源语言，验证它
    if source_language and not validate_language_code(source_language):
        raise ValueError(f"不支持的源语言: {source_language}")
    
    # 构建input数组
    input_array = []
    for i, item in enumerate(input_items):
        input_item = {
            "role": "user",
            "content": [
                {
                    "type": "input_text", 
                    "text": str(item.get("text", ""))
                }
            ]
        }
        
        # 添加翻译选项
        translation_options = {"target_language": target_language}
        if source_language:
            translation_options["source_language"] = source_language
            
        input_item["content"][0]["translation_options"] = translation_options
        
        input_array.append(input_item)
    
    return {
        "model": model,
        "input": input_array,
        "response_format": {"type": "json_object"}
    }