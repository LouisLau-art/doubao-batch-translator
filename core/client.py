#!/usr/bin/env python3
"""
Doubao API Client - 终极版
特性：智能双模 + 动态并发 + 熔断机制 + 身份显式日志
"""

import asyncio
import httpx
import logging
import os
import re
from typing import List, Dict, Set

from core.token_tracker import TokenTracker
from core.config import DOUBAO_TRANSLATION_URL, DOUBAO_CHAT_URL

logger = logging.getLogger(__name__)

# 阈值：超过此长度直接使用大模型
THRESHOLD_TOKENS_FOR_LARGE_MODEL = 700

class AsyncDoubaoClient:
    def __init__(self, api_key: str, models: List[str], max_concurrent: int = 30):
        self.api_key = api_key
        self.models = models if models else ["doubao-seed-translation-250915"]
        self.token_tracker = TokenTracker()
        
        # 熔断列表：记录已经彻底挂掉的模型
        self.disabled_models: Set[str] = set()
        
        # --- 动态并发控制 ---
        self.sem_high = asyncio.Semaphore(max_concurrent)
        low_limit = min(5, max_concurrent) 
        self.sem_low = asyncio.Semaphore(low_limit)
        
        logger.info(f"并发策略初始化: 高性能模式={max_concurrent}, 保守模式={low_limit}")
        
        self.client = httpx.AsyncClient(
            timeout=90.0,
            limits=httpx.Limits(max_keepalive_connections=max_concurrent, max_connections=max_concurrent + 10),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )

    def _get_semaphore(self, model: str) -> asyncio.Semaphore:
        model_lower = model.lower()
        low_limit_keywords = ["seed-translation", "kimi"]
        if any(kw in model_lower for kw in low_limit_keywords):
            return self.sem_low
        return self.sem_high

    async def async_translate(self, text: str, source: str = "en", target: str = "zh") -> str:
        if not text.strip(): return text

        est_tokens = self.token_tracker.estimate_tokens(text)
        start_index = 0
        
        # 长文本跳过策略 (跳过第一个 Seed 模型)
        if est_tokens > THRESHOLD_TOKENS_FOR_LARGE_MODEL and len(self.models) > 1:
            if "seed" in self.models[0]:
                start_index = 1

        last_exception = None
        
        # 遍历模型池
        for i in range(start_index, len(self.models)):
            model = self.models[i]
            
            # 熔断检查
            if model in self.disabled_models:
                continue

            semaphore = self._get_semaphore(model)
            
            async with semaphore:
                try:
                    retries = 2 if i == 0 else 1
                    for attempt in range(retries):
                        try:
                            if self._is_translation_special_model(model):
                                return await self._request_special_endpoint(text, source, target, model)
                            else:
                                return await self._request_chat_endpoint(text, source, target, model)
                        
                        except Exception as e:
                            error_str = str(e)
                            
                            # 严重错误熔断
                            if "SetLimitExceeded" in error_str or "insufficient_quota" in error_str:
                                logger.error(f"🚫 模型 {model} 额度用尽，已永久拉黑。")
                                self.disabled_models.add(model)
                                raise e 

                            if attempt == retries - 1:
                                raise e
                            await asyncio.sleep(1)
                    break 
                            
                except Exception as e:
                    last_exception = e
                    continue 

        if last_exception:
            logger.error(f"❌ 翻译失败 (所有可用模型均尝试失败)")
        return "[TRANSLATION_FAILED]"

    def _is_translation_special_model(self, model_name: str) -> bool:
        return "seed-translation" in model_name

    def _get_system_prompt(self, target_lang: str) -> str:
        lang_map = {"zh": "Simplified Chinese", "en": "English", "jp": "Japanese"}
        target_name = lang_map.get(target_lang, target_lang)
        return (
            f"You are a professional literary translator. Translate into {target_name}.\n"
            "Rules:\n"
            "1. Output ONLY the translation. No notes/explanations.\n"
            "2. Keep original style and tone.\n"
            "3. Handle fragments as fragments."
        )

    async def _request_special_endpoint(self, text: str, source: str, target: str, model: str) -> str:
        """Seed 模型接口"""
        payload = {
            "model": model,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": text, 
                       "translation_options": {"source_language": source, "target_language": target}}]}]
        }
        response = await self.client.post(DOUBAO_TRANSLATION_URL, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Seed API {response.status_code}: {response.text}")
            
        # [新增] 成功日志
        logger.info(f"✅ [{model}] 翻译成功")
        return response.json()["output"][0]["content"][0]["text"].strip()

    async def _request_chat_endpoint(self, text: str, source: str, target: str, model: str) -> str:
        """通用 Chat 接口"""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt(target)},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "temperature": 0.3
        }
        response = await self.client.post(DOUBAO_CHAT_URL, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Chat API {response.status_code}: {response.text}")
            
        # [新增] 成功日志
        logger.info(f"✅ [{model}] 翻译成功")
        return response.json()["choices"][0]["message"]["content"].strip()

    async def close(self):
        await self.client.aclose()


class AsyncTranslator:
    """适配器"""
    def __init__(self, config_or_key):
        if isinstance(config_or_key, str):
            models = ["doubao-seed-translation-250915"]
            api_key = config_or_key
            max_concurrent = 20
        else:
            api_key = config_or_key.api_key
            models = getattr(config_or_key, 'models', [])
            max_concurrent = getattr(config_or_key, 'max_concurrent', 30)
            
            if not models and hasattr(config_or_key, 'model'):
                models = [config_or_key.model]
                
        self.client = AsyncDoubaoClient(api_key, models, max_concurrent)
    
    async def translate_batch(self, texts: List[str], source_lang: str = "en", target_lang: str = "zh") -> List[str]:
        tasks = [
            self.client.async_translate(text, source_lang, target_lang)
            for text in texts
        ]
        return await asyncio.gather(*tasks)
    
    async def close(self):
        await self.client.close()
    
    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.close()