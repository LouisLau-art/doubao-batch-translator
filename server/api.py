#!/usr/bin/env python3
"""
FastAPI服务器 - 适配OpenAI格式
为"沉浸式翻译"插件提供HTTP API服务
"""

import asyncio
import logging
import traceback
import json
import time
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# [修复 1] 正确导入路径
from core.client import AsyncTranslator
from core.config import TranslatorConfig

logger = logging.getLogger(__name__)


# Pydantic模型定义
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(description="模型名称")
    messages: List[Message] = Field(description="对话消息列表")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1000)
    stream: bool = Field(default=False)
    # 沉浸式翻译插件可能会通过 extra_body 传参，也可能不传，这里做兼容
    source_language: Optional[str] = None
    target_language: str = "zh"


class DoubaoServer:
    """豆包翻译API服务器"""
    
    def __init__(self, config: TranslatorConfig):
        self.config = config
        self.translator: Optional[AsyncTranslator] = None
        
        # [修复 2] 使用 lifespan 管理生命周期
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动时初始化
            logger.info("初始化翻译器连接池...")
            self.translator = AsyncTranslator(
                api_key=self.config.api_key,
                model=self.config.model
            )
            yield
            # 关闭时清理
            logger.info("正在关闭翻译器连接池...")
            if self.translator:
                await self.translator.close()
        
        self.app = FastAPI(
            title="豆包翻译API服务器",
            version="2.0.0",
            lifespan=lifespan
        )
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._register_routes()
    
    def _register_routes(self):
        
        @self.app.get("/", summary="健康检查")
        async def health_check():
            return {"status": "healthy", "service": "doubao-translator"}
        
        @self.app.get("/v1/models")
        async def list_models():
            return {
                "object": "list",
                "data": [{
                    "id": "doubao-seed-translation-250915",
                    "object": "model",
                    "created": 0,
                    "owned_by": "bytedance"
                }]
            }
        
        @self.app.post("/v1/chat/completions")
        async def create_chat_completion(request: ChatCompletionRequest):
            logger.info(f"收到请求: {request.model}")
            
            # 心跳检测
            if not request.messages:
                logger.info("空消息列表，返回心跳成功")
                return {
                    "id": "test-conn", 
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "choices": [{"index":0, "message":{"role":"assistant", "content":"OK"}, "finish_reason":"stop"}]
                }
            
            # 提取用户消息
            user_msg = next((m.content for m in reversed(request.messages) if m.role == "user"), None)
            if not user_msg:
                raise HTTPException(status_code=400, detail="未找到用户消息")
            
            # [修复 3] 确保 translator 存在 (lifespan 有时在测试环境可能没触发)
            if not self.translator:
                 self.translator = AsyncTranslator(self.config.api_key, self.config.model)
            
            try:
                # 执行翻译
                # 注意：request.target_language 默认是 zh，如果插件没传该参数可能会有问题
                # 沉浸式翻译插件通常会在 system prompt 里写 "Translate to Chinese" 或者直接传参
                # 这里我们假设插件已配置正确
                
                start_time = time.time()
                results = await self.translator.translate_batch(
                    texts=[user_msg],
                    source_lang=request.source_language or "auto", # 支持自动检测
                    target_lang=request.target_language
                )
                duration = time.time() - start_time
                
                translated_text = results[0] if results else ""
                
                # 检查是否翻译失败
                if translated_text == "[TRANSLATION_FAILED]":
                    logger.error("翻译失败")
                    raise HTTPException(status_code=502, detail="Upstream Translation Failed")

                logger.info(f"翻译完成 ({duration:.2f}s): {len(user_msg)} chars -> {len(translated_text)} chars")
                
                return {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": translated_text
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": len(user_msg),
                        "completion_tokens": len(translated_text),
                        "total_tokens": len(user_msg) + len(translated_text)
                    }
                }
                
            except Exception as e:
                logger.error(f"处理请求失败: {e}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=str(e))

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info" if not debug else "debug"
        )


def run_server(host: str = "0.0.0.0", port: int = 8000, api_key: str = None, debug: bool = False):
    if not api_key:
        import os
        api_key = os.getenv("ARK_API_KEY")
        if not api_key:
            print("错误: 未提供 API Key")
            return
            
    config = TranslatorConfig(api_key=api_key)
    server = DoubaoServer(config)
    server.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server()