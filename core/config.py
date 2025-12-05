#!/usr/bin/env python3
"""
核心配置模块 (Final Fix)
优先级：models.json > ARK_MODELS > 默认值
"""

import os
import json
import logging
from typing import List, Optional
from dataclasses import dataclass, field
from pathlib import Path

# 加载.env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# 常量
DOUBAO_TRANSLATION_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
DOUBAO_CHAT_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_API_KEY_ENV = "ARK_API_KEY"
DEFAULT_MAX_CONCURRENT = 150       
DEFAULT_MAX_REQUESTS_PER_SECOND = 100.0 
DEFAULT_TIMEOUT = 60.0             
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_INPUT_TOKENS = 900
DEFAULT_MODEL_LIST = ["doubao-seed-translation-250915"]

# 支持语言 (略，保持不变)
SUPPORTED_LANGUAGES = {
    "zh": "中文（简体）",
    "zh-Hant": "中文（繁体）",
    "en": "英语",
    "de": "德语", "fr": "法语", "es": "西班牙语", "it": "意大利语",
    "pt": "葡萄牙语", "ru": "俄语", "ja": "日语", "ko": "韩语",
    "th": "泰语", "vi": "越南语", "ar": "阿拉伯语",
}

@dataclass
class TranslatorConfig:
    api_key: str
    models: List[str] = field(default_factory=lambda: DEFAULT_MODEL_LIST)
    max_concurrent: int = 30
    max_requests_per_second: float = 20.0
    timeout: float = 60.0
    max_retries: int = 3
    api_url: str = DOUBAO_TRANSLATION_URL
    source_language: str = ""
    target_language: str = "zh"
    
    @property
    def model(self) -> str:
        return self.models[0] if self.models else "doubao-seed-translation-250915"

    @classmethod
    def from_env(cls) -> 'TranslatorConfig':
        api_key = os.getenv(DOUBAO_API_KEY_ENV)
        
        # --- 核心修改：模型加载逻辑 ---
        models = []
        
        # 1. 优先：models.json
        current_dir = Path(__file__).parent.absolute() # core/
        project_root = current_dir.parent              # root/
        json_path = project_root / "models.json"
        
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        models = [str(m).strip() for m in data if m]
                        print(f"✅ 已加载 models.json: {len(models)} 个模型")
            except Exception as e:
                print(f"⚠️ models.json 读取失败: {e}")

        # 2. 次选：环境变量 ARK_MODELS
        if not models:
            env_models = os.getenv("ARK_MODELS")
            if env_models:
                models = [m.strip() for m in env_models.split(",") if m.strip()]

        # 3. 保底：默认列表
        if not models:
            models = DEFAULT_MODEL_LIST
            
        # 打印调试信息
        print(f"📋 当前生效模型池 (Top 3): {models[:3]}...")

        # --- 核心修改：并发参数加载 ---
        # 优先读取 MAX_CONCURRENT_REQUESTS (你的.env写法)，其次 MAX_CONCURRENT
        env_concurrent = os.getenv('MAX_CONCURRENT_REQUESTS') or os.getenv('MAX_CONCURRENT')
        max_concurrent = int(env_concurrent) if env_concurrent else 30
        
        # 优先读取 REQUESTS_PER_MINUTE 计算 RPS，其次 MAX_REQUESTS_PER_SECOND
        rpm = os.getenv('REQUESTS_PER_MINUTE')
        if rpm:
            max_rps = float(rpm) / 60.0
        else:
            max_rps = float(os.getenv('MAX_REQUESTS_PER_SECOND', "20.0"))

        return cls(
            api_key=api_key if api_key else "",
            models=models,
            max_concurrent=max_concurrent,
            max_requests_per_second=max_rps,
            source_language=os.getenv('SOURCE_LANGUAGE', ""),
            target_language=os.getenv('TARGET_LANGUAGE', "zh"),
        )
    
    @classmethod 
    def from_args(cls, api_key: Optional[str] = None, **kwargs) -> 'TranslatorConfig':
        config = cls.from_env()
        if api_key: config.api_key = api_key
        for key, value in kwargs.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        if not config.api_key:
            raise ValueError(f"未找到API密钥。请设置{DOUBAO_API_KEY_ENV}环境变量")
        return config

def validate_language_code(lang_code: str) -> bool:
    return lang_code in SUPPORTED_LANGUAGES

def get_language_name(lang_code: str) -> Optional[str]:
    return SUPPORTED_LANGUAGES.get(lang_code)