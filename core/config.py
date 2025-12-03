#!/usr/bin/env python3
"""
核心配置模块
包含豆包API常量、配置管理和语言支持定义
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# 加载.env文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# 豆包API配置常量
DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
DOUBAO_MODEL = "doubao-seed-translation-250915"
DOUBAO_API_KEY_ENV = "ARK_API_KEY"

# 默认配置 (已调优以适配高并发)
DEFAULT_MAX_CONCURRENT = 20        # 默认并发数提升到 20
DEFAULT_MAX_REQUESTS_PER_SECOND = 10.0 # 默认 RPS
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_INPUT_TOKENS = 900     # 留出 buffer (模型限制1k)

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
    
    # 亚洲语言
    "ja": "日语",
    "ko": "韩语",
    "th": "泰语",
    "vi": "越南语",
    
    # 其他
    "ar": "阿拉伯语",
}


@dataclass
class TranslatorConfig:
    """翻译器配置类"""
    api_key: str
    api_url: str = DOUBAO_API_URL
    model: str = DOUBAO_MODEL
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    max_requests_per_second: float = DEFAULT_MAX_REQUESTS_PER_SECOND
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    
    def __post_init__(self):
        """验证配置参数"""
        if not self.api_key:
            # 允许初始化为空，后续检查，或者在这里严格检查
            pass
        
        if self.max_concurrent <= 0:
            raise ValueError("最大并发数必须大于0")
            
        if self.max_requests_per_second <= 0:
            raise ValueError("每秒最大请求数必须大于0")
    
    @classmethod
    def from_env(cls) -> 'TranslatorConfig':
        """从环境变量创建配置"""
        api_key = os.getenv(DOUBAO_API_KEY_ENV)
        
        return cls(
            api_key=api_key if api_key else "", # 允许空，后续处理
            api_url=os.getenv('DOUBAO_API_URL', DOUBAO_API_URL),
            model=os.getenv('DOUBAO_MODEL', DOUBAO_MODEL),
            max_concurrent=int(os.getenv('MAX_CONCURRENT', str(DEFAULT_MAX_CONCURRENT))),
            max_requests_per_second=float(os.getenv('MAX_REQUESTS_PER_SECOND', str(DEFAULT_MAX_REQUESTS_PER_SECOND))),
            timeout=float(os.getenv('REQUEST_TIMEOUT', str(DEFAULT_TIMEOUT))),
            max_retries=int(os.getenv('MAX_RETRIES', str(DEFAULT_MAX_RETRIES))),
        )
    
    @classmethod 
    def from_args(cls, api_key: Optional[str] = None, **kwargs) -> 'TranslatorConfig':
        """从参数创建配置 (优先级: 参数 > 环境变量 > 默认值)"""
        # 1. 先加载环境变量配置
        config = cls.from_env()
        
        # 2. 如果提供了 API Key，覆盖环境变量
        if api_key:
            config.api_key = api_key
            
        # 3. 覆盖其他参数
        for key, value in kwargs.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        
        # 4. 最终检查
        if not config.api_key:
            raise ValueError(f"未找到API密钥。请设置{DOUBAO_API_KEY_ENV}环境变量或通过参数传入")
            
        return config


def validate_language_code(lang_code: str) -> bool:
    """验证语言代码是否受支持"""
    return lang_code in SUPPORTED_LANGUAGES


def get_language_name(lang_code: str) -> Optional[str]:
    """获取语言代码对应的语言名称"""
    return SUPPORTED_LANGUAGES.get(lang_code)

# 注意：移除了 format_api_request，因为 client.py 内部实现了特定的 payload 构造逻辑，
# 且该模型不支持标准的 list input，避免误用。