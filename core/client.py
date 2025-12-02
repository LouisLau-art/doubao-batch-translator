#!/usr/bin/env python3
"""
Doubao API Client - 单请求高并发翻译客户端
专门适配 doubao-seed-translation-250915 模型，该模型不支持批量请求
"""

import json
import asyncio
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranslationRequest:
    """翻译请求配置"""
    text: str
    source_language: str = "en"
    target_language: str = "zh"


class AsyncDoubaoClient:
    """异步豆包翻译客户端"""
    
    def __init__(self, api_key: str, model: str = "doubao-seed-translation-250915"):
        """初始化客户端
        
        Args:
            api_key: API密钥
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        self.semaphore = asyncio.Semaphore(20)  # 限制最大并发数为20
        self.timeout = 30.0
        
        # 请求头配置
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def async_translate(self, text: str, source: str = "en", target: str = "zh") -> str:
        """异步翻译单个文本
        
        Args:
            text: 待翻译文本
            source: 源语言代码
            target: 目标语言代码
            
        Returns:
            翻译结果文本
        """
        # 构建单个文本的请求
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text,
                            "translation_options": {
                                "source_language": source,
                                "target_language": target
                        }
                    ]
                }
            ]
        }
        
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json=payload
                    )
                    
                    # 检查响应状态
                    if response.status_code != 200:
                        error_msg = f"API请求失败 (状态码: {response.status_code})"
                        if response.text:
                            error_msg += f": {response.text}"
                        raise Exception(error_msg)
                    
                response_data = response.json()
                
                # 解析豆包API特有响应格式
                if "output" in response_data:
                    output_list = response_data["output"]
                    if not output_list or not isinstance(output_list, list):
                        raise Exception("API响应中output字段格式错误")
                    
                    first_output = output_list[0]
                    content_list = first_output.get("content", [])
                    if not content_list or not isinstance(content_list, list):
                        raise Exception("API响应中content字段格式错误")
                    
                    translated_text = content_list[0].get("text", "")
                    logger.debug(f"翻译结果: {translated_text[:50]}...")
                    return translated_text.strip()
                else:
                    raise Exception("API响应格式不匹配")
                    
            except httpx.RequestError as e:
                logger.error(f"网络请求失败: {e}")
                raise Exception(f"网络请求失败: {e}")
    
    async def close(self):
        """关闭客户端连接"""
        pass  # httpx客户端会自动管理连接


# 兼容性包装函数
async def translate_text(text: str, api_key: str, source: str = "en", target: str = "zh") -> str:
    """翻译单个文本的兼容性函数
    
    Args:
        text: 待翻译文本
        api_key: API密钥
        source: 源语言代码
        target: 目标语言代码
    
    Returns:
        翻译结果文本
    """
    client = AsyncDoubaoClient(api_key)
    try:
        return await client.async_translate(text, source, target)
    finally:
        await client.close()