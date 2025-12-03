#!/usr/bin/env python3
"""
Doubao API Client - 单请求高并发翻译客户端
专门适配 doubao-seed-translation-250915 模型
包含连接池复用、重试机制和错误处理
"""

import json
import asyncio
import httpx
import logging
import os
from typing import Optional, Dict, Any, List, Union

from core.token_tracker import TokenTracker

logger = logging.getLogger(__name__)

# 模型限制 - 设置为800以留出足够误差余地
MAX_TOKEN_PER_TEXT = 800  # 最大输入Token长度

class AsyncDoubaoClient:
    """异步豆包翻译客户端 (支持连接复用与重试)"""
    
    def __init__(self, api_key: str, model: str = "doubao-seed-translation-250915"):
        """初始化客户端"""
        self.api_key = api_key
        self.model = model
        self.token_tracker = TokenTracker()
        # 优先从环境变量读取 Endpoint，否则使用默认值
        self.api_url = os.getenv("API_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3/responses")
        
        # 并发控制
        self.semaphore = asyncio.Semaphore(20)  # 限制并发数为20
        
        # 共享的 HTTP 客户端 (关键优化：复用连接池)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=30),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1.0  # 基础等待秒数

    def _split_text(self, text: str) -> List[str]:
        """将长文本拆分为符合模型token限制的小块"""
        if not text:
            return []
            
        # 估算当前文本的token数量
        estimated_tokens = self.token_tracker.estimate_tokens(text)
        
        # 如果不超过限制，直接返回
        if estimated_tokens <= MAX_TOKEN_PER_TEXT:
            return [text]
            
        # 尝试按句子拆分
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        
        # 合并句子，确保每个块不超过token限制
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.token_tracker.estimate_tokens(sentence)
            
            # 如果单个句子就超过限制，进一步按段落拆分
            if sentence_tokens > MAX_TOKEN_PER_TEXT:
                paragraphs = sentence.split('\n\n')
                
                for paragraph in paragraphs:
                    paragraph_tokens = self.token_tracker.estimate_tokens(paragraph)
                    
                    # 如果单个段落仍超过限制，按逗号拆分
                    if paragraph_tokens > MAX_TOKEN_PER_TEXT:
                        segments = paragraph.split(',')
                        
                        for segment in segments:
                            segment_tokens = self.token_tracker.estimate_tokens(segment)
                            
                            if segment_tokens > MAX_TOKEN_PER_TEXT:
                                # 极端情况：按空格拆分
                                words = segment.split()
                                temp_chunk = ""
                                temp_tokens = 0
                                
                                for word in words:
                                    word_tokens = self.token_tracker.estimate_tokens(word + ' ')
                                    
                                    if temp_tokens + word_tokens > MAX_TOKEN_PER_TEXT and temp_chunk:
                                        chunks.append(temp_chunk.strip())
                                        temp_chunk = ""
                                        temp_tokens = 0
                                        
                                    temp_chunk += word + ' '
                                    temp_tokens += word_tokens
                                    
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                            else:
                                chunks.append(segment.strip() + ',')
                    else:
                        chunks.append(paragraph.strip())
            else:
                # 合并句子
                new_tokens = current_tokens + sentence_tokens
                
                if new_tokens > MAX_TOKEN_PER_TEXT:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                else:
                    current_chunk += ' ' + sentence if current_chunk else sentence
                    current_tokens = new_tokens
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        # 清理可能的重复标点
        chunks = [re.sub(r'([.!?。！？,])\1+', r'\1', chunk) for chunk in chunks]
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        
        return chunks

    async def async_translate(self, text: str, source: str = "en", target: str = "zh") -> str:
        """异步翻译单个文本 (带重试机制)"""
        
        # 拆分长文本
        chunks = self._split_text(text)
        
        # 如果只有一个块，直接翻译
        if len(chunks) == 1:
            # 构造豆包特有的 Payload
            payload = {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": chunks[0],
                                "translation_options": {
                                    "source_language": source,
                                    "target_language": target
                                }
                            }
                        ]
                    }
                ]
            }
            
            async with self.semaphore:
                for attempt in range(self.max_retries):
                    try:
                        response = await self.client.post(self.api_url, json=payload)
                        
                        # 处理限流 (429) 和服务器错误 (5xx)
                        if response.status_code == 429 or response.status_code >= 500:
                            error_msg = f"HTTP {response.status_code}"
                            if attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                                logger.warning(f"请求失败 ({error_msg})，{wait_time}秒后重试... [尝试 {attempt+1}/{self.max_retries}]")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                response.raise_for_status()

                        response.raise_for_status() # 检查其他错误
                        return self._parse_response(response.json())
                        
                    except httpx.RequestError as e:
                        # 网络层面的错误（如连接超时、DNS 失败）
                        if attempt < self.max_retries - 1:
                            logger.warning(f"网络错误: {e}，正在重试... [尝试 {attempt+1}/{self.max_retries}]")
                            await asyncio.sleep(1)
                        else:
                            logger.error(f"网络请求最终失败: {e}")
                            raise Exception(f"翻译请求失败: {e}")
                    
                    except Exception as e:
                        # 其他不可预知的错误
                        logger.error(f"翻译过程中发生错误: {e}")
                        raise e
        
        # 如果有多个块，递归调用翻译每个块，然后合并结果
        tasks = [self.async_translate(chunk, source, target) for chunk in chunks]
        results = await asyncio.gather(*tasks)
        
        # 合并结果并返回
        return ' '.join(results)

    def _parse_response(self, response_data: Dict) -> str:
        """解析豆包API响应"""
        try:
            if "output" in response_data:
                output_list = response_data["output"]
                if output_list and isinstance(output_list, list):
                    first_output = output_list[0]
                    content_list = first_output.get("content", [])
                    if content_list and isinstance(content_list, list):
                        return content_list[0].get("text", "").strip()
            
            # 如果结构不匹配，记录日志并抛出
            logger.error(f"API响应格式异常: {response_data}")
            raise Exception("API响应格式无法解析")
            
        except Exception as e:
            raise Exception(f"解析响应数据失败: {e}")

    async def close(self):
        """关闭客户端连接池"""
        await self.client.aclose()


class AsyncTranslator:
    """批量翻译适配器"""
    
    def __init__(self, api_key: str, model: str = "doubao-seed-translation-250915"):
        self.client = AsyncDoubaoClient(api_key, model)
    
    async def translate_batch(self, texts: List[str], source_lang: str = "en", target_lang: str = "zh") -> List[str]:
        """批量并发翻译"""
        tasks = [
            self.client.async_translate(text, source_lang, target_lang)
            for text in texts
        ]
        # return_exceptions=True 允许部分成功，而不是一个报错全部崩溃
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果，将异常转换为特定的错误文本，防止后续流程崩溃
        final_results = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"批处理中单个任务失败: {res}")
                final_results.append("[TRANSLATION_FAILED]") # 标记失败
            else:
                final_results.append(res)
        return final_results
    
    async def close(self):
        await self.client.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()