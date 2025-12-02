#!/usr/bin/env python3
"""
异步翻译器核心类
提供高效的大规模文本翻译功能，支持批处理、并发控制和智能重试
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Union
from collections import deque

import httpx

from .config import TranslatorConfig, format_api_request, validate_language_code
from .exceptions import (
    APIError, RateLimitError, AuthenticationError, ConfigurationError,
    ValidationError, NetworkError, TimeoutError, UnsupportedLanguageError,
    BatchProcessingError
)


logger = logging.getLogger(__name__)


class AsyncTranslator:
    """异步批量翻译器核心类"""
    
    def __init__(self, config: TranslatorConfig):
        """初始化翻译器
        
        Args:
            config: 翻译器配置
        """
        if not isinstance(config, TranslatorConfig):
            raise ConfigurationError("配置必须是TranslatorConfig类型")
        
        self.config = config
        self.api_url = config.api_url
        self.model = config.model
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        
        # HTTP客户端
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self.rate_limit_window = deque()
        self.max_requests_per_second = config.max_requests_per_second
        
        # 客户端会话
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.aclose()
    
    async def _rate_limit(self):
        """频率限制控制"""
        now = datetime.now()
        window_start = now.replace(second=now.second, microsecond=0)
        
        # 清理过期请求记录
        while self.rate_limit_window and self.rate_limit_window[0] < window_start:
            self.rate_limit_window.popleft()
        
        # 检查是否超过限制
        if len(self.rate_limit_window) >= self.max_requests_per_second:
            # 计算需要等待的时间
            earliest_request = self.rate_limit_window[0]
            wait_time = 1.0 - (now - earliest_request).total_seconds()
            if wait_time > 0:
                logger.debug(f"频率限制，等待 {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)
                return await self._rate_limit()  # 重新检查
        
        # 记录本次请求
        self.rate_limit_window.append(now)
    
    async def _make_api_request(self, payload: Dict) -> Dict:
        """发起API请求"""
        await self._rate_limit()
        
        for attempt in range(self.max_retries + 1):
            try:
                if not self.client:
                    self.client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
                
                response = await self.client.post(self.api_url, json=payload)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # 频率限制错误
                    raise RateLimitError(f"请求过于频繁 (状态码: 429)")
                elif response.status_code == 401:
                    # 认证错误
                    raise AuthenticationError("API密钥无效或已过期")
                elif response.status_code >= 500:
                    # 服务器错误，重试
                    if attempt < self.max_retries:
                        delay = 2 ** attempt  # 指数退避
                        logger.warning(f"服务器错误 (状态码: {response.status_code})，{delay}秒后重试")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise APIError(f"服务器持续错误 (状态码: {response.status_code})")
                else:
                    # 其他客户端错误
                    error_msg = f"API请求失败 (状态码: {response.status_code})"
                    if response.text:
                        error_msg += f": {response.text}"
                    raise APIError(error_msg, response.status_code, response.text)
            
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    delay = 2 ** attempt
                    logger.warning(f"请求超时，{delay}秒后重试 (第{attempt + 1}次)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TimeoutError(f"请求最终超时 (超过{self.max_retries}次重试)")
            
            except httpx.RequestError as e:
                if attempt < self.max_retries:
                    delay = 2 ** attempt
                    logger.warning(f"网络错误: {e}，{delay}秒后重试 (第{attempt + 1}次)")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise NetworkError(f"网络错误 (超过{self.max_retries}次重试): {e}")
        
        # 理论上不会到达这里
        raise APIError("达到最大重试次数，API请求失败")
    
    def _validate_batch_items(self, items: List[Dict]) -> List[Dict]:
        """验证和清理批次项目"""
        validated_items = []
        
        for i, item in enumerate(items):
            try:
                # 验证基本字段
                if not isinstance(item, dict):
                    raise ValidationError(f"项目 {i} 不是字典类型")
                
                text = str(item.get("text", "")).strip()
                if not text:
                    logger.warning(f"跳过空文本项目 {i}")
                    continue
                
                validated_items.append({
                    "text": text,
                    "index": i,
                    **{k: v for k, v in item.items() if k != "text"}
                })
            
            except Exception as e:
                logger.warning(f"验证项目 {i} 失败: {e}")
                continue
        
        if not validated_items:
            raise ValidationError("没有有效的翻译项目")
        
        return validated_items
    
    def _create_optimal_batches(self, items: List[Dict]) -> List[List[Dict]]:
        """创建优化的批次"""
        if not items:
            return []
        
        batches = []
        current_batch = []
        current_chars = 0
        
        for item in items:
            item_text = item["text"]
            item_chars = len(item_text)
            
            # 检查是否需要开始新批次
            if (current_batch and 
                (current_chars + item_chars > self.config.max_chars_per_batch or 
                 len(current_batch) >= self.config.batch_size)):
                
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
            
            current_batch.append(item)
            current_chars += item_chars
        
        # 添加最后一个批次
        if current_batch:
            batches.append(current_batch)
        
        logger.info(f"创建了 {len(batches)} 个批次，总计 {len(items)} 个项目")
        return batches
    
    async def _translate_batch(self, batch: List[Dict], source_lang: Optional[str], 
                              target_lang: str) -> List[Dict]:
        """翻译单个批次"""
        if not batch:
            return []
        
        # 验证语言代码
        if not validate_language_code(target_lang):
            raise UnsupportedLanguageError(target_lang)
        
        if source_lang and not validate_language_code(source_lang):
            raise UnsupportedLanguageError(source_lang)
        
        async with self.semaphore:
            try:
                # 构建请求
                payload = format_api_request(
                    model=self.model,
                    input_items=batch,
                    source_language=source_lang,
                    target_language=target_lang
                )
                
                logger.debug(f"翻译批次: {len(batch)} 个项目")
                
                # 发送请求
                response = await self._make_api_request(payload)
                
                # 解析响应
                return self._parse_response(response, batch)
            
            except Exception as e:
                logger.error(f"批次翻译失败: {e}")
                raise BatchProcessingError(
                    f"批次翻译失败: {e}",
                    batch_items=[item["text"] for item in batch]
                )
    
    def _parse_response(self, response: Dict, batch: List[Dict]) -> List[Dict]:
        """解析API响应"""
        try:
            # 豆包API响应格式处理
            if "choices" in response:
                # OpenAI格式
                choices = response.get("choices", [])
                if not choices:
                    raise APIError("API响应中没有choices字段")
                message_content = choices[0].get("message", {}).get("content", "{}")
            elif "output" in response:
                # 豆包API格式
                output_list = response["output"]
                if not output_list or not isinstance(output_list, list):
                    raise APIError("API响应中output字段格式错误")
                first_output = output_list[0]
                content_list = first_output.get("content", [])
                if not content_list or not isinstance(content_list, list):
                    raise APIError("API响应中content字段格式错误")
                message_content = content_list[0].get("text", "")
            else:
                # 直接使用响应内容
                message_content = str(response)
            
            # 直接返回翻译文本内容
            if isinstance(message_content, str):
                translated_text = message_content.strip()
            else:
                # 尝试解析JSON（备用）
                try:
                    content_data = json.loads(message_content)
                    translated_text = content_data.get("translation", str(message_content))
                except (json.JSONDecodeError, TypeError):
                    translated_text = str(message_content)
            
            # 返回单个项目的翻译结果
            if len(batch) == 1:
                return [{
                    "original": batch[0]["text"],
                    "translated": translated_text,
                    "index": batch[0].get("index", 0),
                    "translated_at": datetime.now().isoformat()
                }]
            else:
                # 批处理模式（备用）
                results = []
                for i, item in enumerate(batch):
                    result = {
                        "original": item["text"],
                        "translated": translated_text if i == 0 else "",
                        "index": item.get("index", i),
                        "translated_at": datetime.now().isoformat()
                    }
                    
                    # 保留原始项目的其他字段
                    for key, value in item.items():
                        if key not in ["text", "index"] and key not in result:
                            result[key] = value
                    
                    results.append(result)
                
                return results
        
        except Exception as e:
            logger.error(f"解析API响应失败: {e}")
            raise APIError(f"解析API响应失败: {e}")
    
    async def translate_batch(self, texts: List[str], source_lang: Optional[str] = None, 
                             target_lang: str = "zh", 
                             progress_callback: Optional[Callable] = None) -> List[Dict]:
        """翻译一批文本
        
        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码（可选）
            target_lang: 目标语言代码（必选）
            progress_callback: 进度回调函数
            
        Returns:
            翻译结果列表
        """
        if not texts:
            return []
        
        logger.info(f"开始批量翻译: {len(texts)} 个文本")
        
        # 构建项目列表
        items = [{"text": text} for text in texts]
        
        # 验证和创建批次
        validated_items = self._validate_batch_items(items)
        batches = self._create_optimal_batches(validated_items)
        
        # 翻译所有批次
        all_results = []
        total_batches = len(batches)
        
        async with self:  # 使用上下文管理器确保客户端正确关闭
            for i, batch in enumerate(batches):
                try:
                    if progress_callback:
                        progress = (i + 1) / total_batches
                        await progress_callback(progress, f"批次 {i + 1}/{total_batches}")
                    
                    batch_results = await self._translate_batch(batch, source_lang, target_lang)
                    all_results.extend(batch_results)
                    
                    # 短暂延迟避免过载
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"处理批次 {i + 1} 失败: {e}")
                    # 为失败的批次创建失败结果
                    for item in batch:
                        result = {
                            "original": item["text"],
                            "translated": "",
                            "index": item.get("index", 0),
                            "error": str(e),
                            "translated_at": datetime.now().isoformat()
                        }
                        all_results.append(result)
        
        logger.info(f"批量翻译完成: {len(all_results)} 个结果")
        return all_results
    
    async def translate_single(self, text: str, source_lang: Optional[str] = None, 
                              target_lang: str = "zh") -> str:
        """翻译单个文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（可选）
            target_lang: 目标语言代码（必选）
            
        Returns:
            翻译后的文本
        """
        results = await self.translate_batch([text], source_lang, target_lang)
        
        if results and results[0]:
            return results[0]["translated"]
        else:
            raise APIError("翻译失败或返回空结果")
    
    async def translate_dict_list(self, items: List[Dict], text_field: str = "text",
                                 source_lang: Optional[str] = None, 
                                 target_lang: str = "zh",
                                 result_field: str = "translated",
                                 progress_callback: Optional[Callable] = None) -> List[Dict]:
        """翻译字典列表
        
        Args:
            items: 字典列表，每个字典包含待翻译文本
            text_field: 包含待翻译文本的字段名
            source_lang: 源语言代码（可选）
            target_lang: 目标语言代码（必选）
            result_field: 存储翻译结果的字段名
            progress_callback: 进度回调函数
            
        Returns:
            更新后的字典列表
        """
        if not items:
            return []
        
        logger.info(f"开始翻译字典列表: {len(items)} 个条目")
        
        # 提取文本
        texts = []
        for item in items:
            text = str(item.get(text_field, "")).strip()
            if text:
                texts.append(text)
        
        if not texts:
            logger.warning("没有找到有效的文本内容")
            return items
        
        # 翻译文本
        results = await self.translate_batch(texts, source_lang, target_lang, progress_callback)
        
        # 回填结果
        result_index = 0
        for i, item in enumerate(items):
            text = str(item.get(text_field, "")).strip()
            if not text:
                continue
            
            if result_index < len(results):
                item[result_field] = results[result_index]["translated"]
                result_index += 1
            else:
                item[result_field] = ""
        
        logger.info(f"字典列表翻译完成")
        return items