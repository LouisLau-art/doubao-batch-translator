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
from typing import List, Dict, Set, Optional

from core.token_tracker import TokenTracker
from core.config import DOUBAO_TRANSLATION_URL, DOUBAO_CHAT_URL

logger = logging.getLogger(__name__)



class AsyncDoubaoClient:
    def __init__(self, api_key: str, models: List[str], max_concurrent: int = 150, source_language: str = "", target_language: str = "en"):
        self.api_key = api_key
        self.models = models if models else ["doubao-seed-translation-250915"]
        self.token_tracker = TokenTracker()
        
        # [新增] 统计字典：{模型ID: 成功次数}
        self.model_stats = {
            m: {'calls': 0, 'input': 0, 'output': 0} 
            for m in self.models
        }
        
        # 熔断列表：记录已经彻底挂掉的模型
        self.disabled_models: Set[str] = set()
        
        # --- 优化的并发控制策略 ---
        # doubao-seed-translation-250915: RPM=5000 → 慢车道=80并发
        # 其他高性能模型 (DeepSeek, Doubao Pro等): RPM=30000 → 快车道=500并发
        self.sem_fast = asyncio.Semaphore(500)  # 快车道：500并发 (RPM=30000/60=500)
        self.sem_seed = asyncio.Semaphore(80)   # 慢车道：80并发 (RPM=5000/60≈83)
        
        logger.info(f"🚀 并发策略: 快车道(DeepSeek/Doubao)=500, 慢车道(Seed-Translation)=80")
        
        self.source_language = source_language
        self.target_language = target_language
        self.client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(
                max_keepalive_connections=500,  # 提升到500以支持快车道
                max_connections=550  # 留一点余量
            ),
            
            # [关键修复] 告诉 httpx 忽略所有系统环境变量中的代理设置
            trust_env=False, 
            
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )


    def _get_semaphore(self, model: str) -> asyncio.Semaphore:
        """根据模型类型返回对应的信号量控制器"""
        model_lower = model.lower()
        # 慢车道模型: seed-translation (RPM=5000), kimi-k2 (RPM=5000)
        if "seed-translation" in model_lower or "kimi-k2" in model_lower:
            return self.sem_seed  # 慢车道: 80并发
        return self.sem_fast  # 快车道: 500并发

    async def async_translate(self, text: str, source: str = "", target: str = "en") -> str:
        if not text.strip(): return text

        source = self.source_language
        target = self.target_language

        last_exception = None
        
        for i in range(len(self.models)):
            model = self.models[i]
            
            if model in self.disabled_models:
                continue

            semaphore = self._get_semaphore(model)
            
            async with semaphore:
                # [Check 2] 关键修复：拿到锁之后再次检查！
                # 防止排队期间模型被其他并发请求拉黑
                if model in self.disabled_models:
                    continue

                try:
                    retries = 2 if i == 0 else 1
                    for attempt in range(retries):
                        if model in self.disabled_models:
                            raise Exception("Model disabled during retry")
                        try:
                            if self._is_translation_special_model(model):
                                result, in_t, out_t = await self._request_special_endpoint(text, source, target, model)
                            else:
                                result, in_t, out_t = await self._request_chat_endpoint(text, source, target, model)
                            
                            # 更新详细统计
                            if model not in self.model_stats:
                                self.model_stats[model] = {'calls': 0, 'input': 0, 'output': 0}
                            
                            self.model_stats[model]['calls'] += 1
                            self.model_stats[model]['input'] += in_t
                            self.model_stats[model]['output'] += out_t
                            
                            return result

                        
                        except Exception as e:
                            error_str = str(e).lower()
                            
                            # [情况1] 额度用尽 - 永久拉黑该模型
                            if "setlimitexceeded" in error_str or "insufficient_quota" in error_str:
                                if model not in self.disabled_models:
                                    logger.error(f"🚫 模型 {model} 额度用尽，已永久拉黑。")
                                    self.disabled_models.add(model)
                                raise e
                            
                            # [情况2] 输入过长 - 仅本次请求降级，不拉黑模型
                            # 实测 doubao-seed-translation 超限时返回: 400 InvalidParameter
                            # 其他可能的关键词: context_length_exceeded, too long, max_tokens
                            token_limit_keywords = [
                                "invalidparameter",  # doubao-seed-translation 实际返回
                                "context_length", "too long", "token limit", 
                                "max_token", "length exceed", "input too long"
                            ]
                            if any(kw in error_str for kw in token_limit_keywords):
                                logger.warning(f"⚠️ [{model}] 输入过长 ({len(text)} chars)，降级到下一个模型...")
                                raise e  # 抛出让外层 continue 到下一个模型

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
            
        logger.debug(f"✅ [{model}] 翻译成功")
        result_text = response.json()["output"][0]["content"][0]["text"].strip()
        
        # [新增] 估算 Token (Seed 模型不返回 usage，手动计算)
        in_tokens = self.token_tracker.estimate_tokens(text)
        out_tokens = self.token_tracker.estimate_tokens(result_text)
        
        # [修改] 返回元组 (文本, 输入Token, 输出Token)
        return result_text, in_tokens, out_tokens

    async def _request_chat_endpoint(self, text: str, source: str, target: str, model: str) -> tuple[str, int, int]:
        """通用 Chat 接口 (适配 DeepSeek, Doubao Pro/1.6 等高性能模型)"""
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt(target)},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "temperature": 0.3
        }

        # [新增] 针对 Doubao 1.6 思考模型的特殊处理
        # 强制设置 reasoning_effort 为 minimal (不思考)，变身为纯文本模型
        if "doubao-seed-1-6" in model:
            payload["reasoning_effort"] = "minimal"
            # 1.6 模型通常建议稍微调高一点 max_tokens 防止截断，虽然翻译一般够用
            # payload["max_completion_tokens"] = 4096 

        response = await self.client.post(DOUBAO_CHAT_URL, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Chat API {response.status_code}: {response.text}")
            
        logger.debug(f"✅ [{model}] 翻译成功")
        data = response.json()
        
        # 解析内容
        result_text = data["choices"][0]["message"]["content"].strip()
        
        # 提取 Token (兼容部分模型可能没有 usage 字段的情况)
        usage = data.get("usage", {})
        in_tokens = usage.get("prompt_tokens", 0)
        out_tokens = usage.get("completion_tokens", 0)
        
        return result_text, in_tokens, out_tokens

    async def close(self):
        await self.client.aclose()


class AsyncTranslator:
    """适配器"""
    def __init__(self, config_or_key):
        if isinstance(config_or_key, str):
            models = ["doubao-seed-translation-250915"]
            api_key = config_or_key
            max_concurrent = 20
            source_language = ""
            target_language = "zh"
        else:
            api_key = config_or_key.api_key
            models = getattr(config_or_key, 'models', [])
            max_concurrent = getattr(config_or_key, 'max_concurrent', 30)
            source_language = getattr(config_or_key, 'source_language', "")
            target_language = getattr(config_or_key, 'target_language', "zh")
            
            if not models and hasattr(config_or_key, 'model'):
                models = [config_or_key.model]
                
        self.client = AsyncDoubaoClient(api_key, models, max_concurrent, source_language, target_language)
    
    async def translate_batch(self, texts: List[str], source_lang: Optional[str] = None, target_lang: Optional[str] = None) -> List[str]:
        source = source_lang if source_lang is not None else self.client.source_language
        target = target_lang if target_lang is not None else self.client.target_language
        tasks = [
            self.client.async_translate(text, source, target)
            for text in texts
        ]
        return await asyncio.gather(*tasks)
    
    # [新增] 获取统计信息接口
    def get_stats(self) -> Dict[str, int]:
        return self.client.model_stats

    async def close(self):
        await self.client.close()
    
    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.close()