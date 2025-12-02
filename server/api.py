#!/usr/bin/env python3
"""
FastAPI服务器 - 适配OpenAI格式
为"沉浸式翻译"插件提供HTTP API服务
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from core import AsyncTranslator, TranslatorConfig, ValidationError


logger = logging.getLogger(__name__)


# Pydantic模型定义
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(description="模型名称")
    messages: List[Message] = Field(description="对话消息列表")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4000, description="最大tokens数")
    stream: bool = Field(default=False, description="是否流式输出")
    source_language: Optional[str] = Field(default=None, description="源语言代码")
    target_language: str = Field(default="zh", description="目标语言代码")


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Dict[str, int]


class ErrorResponse(BaseModel):
    error: Dict[str, Any]


class DoubaoServer:
    """豆包翻译API服务器"""
    
    def __init__(self, config: TranslatorConfig):
        """初始化服务器
        
        Args:
            config: 翻译器配置
        """
        self.config = config
        self.translator: Optional[AsyncTranslator] = None
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="豆包翻译API服务器",
            description="适配OpenAI格式的翻译服务",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/", summary="健康检查")
        async def health_check():
            """健康检查接口"""
            return {
                "status": "healthy",
                "service": "doubao-translator",
                "version": "2.0.0",
                "timestamp": "2025-12-02T13:53:00Z"
            }
        
        @self.app.get("/v1/models", summary="获取模型列表")
        async def list_models():
            """获取支持的模型列表"""
            return {
                "object": "list",
                "data": [
                    {
                        "id": "doubao-seed-translation-250915",
                        "object": "model",
                        "created": 0,
                        "owned_by": "bytedance"
                    }
                ]
            }
        
        @self.app.post("/v1/chat/completions", response_model=Union[ChatCompletionResponse, ErrorResponse],
                      summary="聊天完成（翻译接口）")
        async def create_chat_completion(request: ChatCompletionRequest):
            """创建聊天完成（实际为翻译服务）"""
            try:
                # 验证模型
                if request.model != "doubao-seed-translation-250915":
                    raise HTTPException(
                        status_code=400,
                        detail=f"不支持的模型: {request.model}"
                    )
                
                # 验证消息
                if not request.messages:
                    raise HTTPException(status_code=400, detail="消息列表不能为空")
                
                # 获取用户输入
                user_messages = [msg for msg in request.messages if msg.role == "user"]
                if not user_messages:
                    raise HTTPException(status_code=400, detail="需要至少一个用户消息")
                
                user_input = user_messages[-1].content.strip()
                if not user_input:
                    raise HTTPException(status_code=400, detail="用户消息内容不能为空")
                
                # 确保翻译器已初始化
                if not self.translator:
                    self.translator = AsyncTranslator(self.config)
                
                # 执行翻译
                logger.info(f"收到翻译请求: {len(user_input)} 字符")
                
                translated_text = await self.translator.translate_single(
                    text=user_input,
                    source_lang=request.source_language,
                    target_lang=request.target_language
                )
                
                # 构建响应
                response = ChatCompletionResponse(
                    id="chatcmpl-translator-1",
                    created=int(asyncio.get_event_loop().time()),
                    model=request.model,
                    choices=[
                        Choice(
                            index=0,
                            message=Message(role="assistant", content=translated_text),
                            finish_reason="stop"
                        )
                    ],
                    usage={
                        "prompt_tokens": len(user_input) // 4,  # 估算值
                        "completion_tokens": len(translated_text) // 4,  # 估算值
                        "total_tokens": (len(user_input) + len(translated_text)) // 4
                    }
                )
                
                logger.info(f"翻译完成: {len(translated_text)} 字符")
                return response
                
            except ValidationError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"翻译过程中发生错误: {e}")
                raise HTTPException(status_code=500, detail=f"服务器内部错误: {e}")
        
        @self.app.get("/v1/status", summary="服务状态")
        async def service_status():
            """获取服务状态"""
            translator_status = "ready" if self.translator else "not_initialized"
            
            return {
                "service": "doubao-translator",
                "status": "running",
                "translator_status": translator_status,
                "config": {
                    "model": self.config.model,
                    "api_url": self.config.api_url,
                    "max_concurrent": self.config.max_concurrent,
                    "max_requests_per_second": self.config.max_requests_per_second
                },
                "supported_languages": {
                    "source_languages": list({"zh", "zh-Hant", "en", "ja", "ko", "de", "fr", "es", "it", "pt", "ru"}.union(
                        set() if not self.config else set()
                    )),
                    "target_languages": ["zh", "zh-Hant", "en", "ja", "ko", "de", "fr", "es", "it", "pt", "ru"]
                }
            }
        
        # 错误处理
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc: HTTPException):
            """HTTP异常处理"""
            logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
            return ErrorResponse(error={
                "code": exc.status_code,
                "message": exc.detail
            })
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request, exc: Exception):
            """通用异常处理"""
            logger.error(f"未处理的异常: {exc}")
            return ErrorResponse(error={
                "code": 500,
                "message": "服务器内部错误"
            })
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """启动服务器
        
        Args:
            host: 绑定地址
            port: 监听端口
            debug: 是否启用调试模式
        """
        logger.info(f"启动豆包翻译服务器: http://{host}:{port}")
        logger.info(f"API文档: http://{host}:{port}/docs")
        logger.info(f"ReDoc文档: http://{host}:{port}/redoc")
        
        uvicorn.run(
            self.get_app(),
            host=host,
            port=port,
            log_level="info" if not debug else "debug"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("豆包翻译API服务器启动")
    
    yield
    
    # 关闭时执行
    logger.info("豆包翻译API服务器关闭")


# 便捷启动函数
def create_server(api_key: str, **config_kwargs) -> DoubaoServer:
    """创建服务器实例
    
    Args:
        api_key: API密钥
        **config_kwargs: 其他配置参数
        
    Returns:
        服务器实例
    """
    config = TranslatorConfig(api_key=api_key, **config_kwargs)
    return DoubaoServer(config)


def run_server(host: str = "0.0.0.0", port: int = 8000, api_key: str = None, debug: bool = False):
    """直接启动服务器
    
    Args:
        host: 绑定地址
        port: 监听端口
        api_key: API密钥
        debug: 是否启用调试模式
    """
    # 获取API密钥
    if not api_key:
        import os
        api_key = os.getenv("ARK_API_KEY")
        if not api_key:
            raise ValueError("请设置ARK_API_KEY环境变量或传入api_key参数")
    
    # 创建并启动服务器
    server = create_server(api_key)
    server.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="启动豆包翻译API服务器")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--api-key", help="API密钥")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    
    args = parser.parse_args()
    
    run_server(
        host=args.host,
        port=args.port,
        api_key=args.api_key,
        debug=args.debug
    )