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
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# [修复 1] 正确导入路径
from core.client import AsyncTranslator
from core.config import TranslatorConfig

# ========== 日志配置 ==========
def setup_logging(debug: bool = False):
    """配置日志系统：同时输出到控制台和文件"""
    # 创建logs目录
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 日志文件名包含日期
    log_file = log_dir / f"server_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 创建格式化器
    console_formatter = logging.Formatter(
        '%(asctime)s │ %(levelname)-7s │ %(message)s',
        datefmt='%H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # 文件Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有DEBUG级别
    file_handler.setFormatter(file_formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除已有handlers（避免重复）
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return log_file

logger = logging.getLogger(__name__)


# Pydantic模型定义
class Message(BaseModel):
    """消息模型 - 兼容多种 content 格式"""
    role: str
    # content 可能是字符串，也可能是数组 (如 OpenAI vision 格式)
    content: Union[str, List[Any], None] = None
    
    model_config = {"extra": "allow"}  # 允许额外字段
    
    def get_text_content(self) -> str:
        """智能提取文本内容"""
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, list):
            # 处理数组格式，如 [{"type": "text", "text": "..."}]
            texts = []
            for item in self.content:
                if isinstance(item, dict):
                    if "text" in item:
                        texts.append(item["text"])
                    elif "content" in item:
                        texts.append(item["content"])
                elif isinstance(item, str):
                    texts.append(item)
            return " ".join(texts)
        return ""


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="doubao-seed-translation-250915", description="模型名称")
    messages: List[Message] = Field(default_factory=list, description="对话消息列表")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1000)
    stream: bool = Field(default=False)
    # 沉浸式翻译插件可能会通过 extra_body 传参，也可能不传，这里做兼容
    source_language: Optional[str] = None
    target_language: str = "zh"
    
    model_config = {"extra": "allow"}  # 允许额外字段，如 n, top_p 等


# ========== 沉浸式翻译专用格式 ==========
class ImmersiveTranslateRequest(BaseModel):
    """沉浸式翻译插件的自定义翻译服务格式"""
    source_lang: Optional[str] = Field(default=None, description="源语言代码")
    target_lang: str = Field(default="zh", description="目标语言代码")
    text_list: List[str] = Field(description="待翻译文本数组")
    
    model_config = {"extra": "allow"}


class ImmersiveTranslateResponse(BaseModel):
    """沉浸式翻译响应格式"""
    translations: List[Dict[str, str]]


# ========== 语言代码映射 ==========
# 沉浸式翻译语言代码 -> Doubao API 语言代码
IMMERSIVE_TO_DOUBAO_LANG = {
    # 特殊处理
    "auto": "",          # 自动检测 -> 空字符串
    
    # 中文变体
    "zh-cn": "zh",       # 简体中文
    "zh-tw": "zh-Hant",  # 繁体中文
    "zh": "zh",          # 兼容直接传 zh
    
    # 直接映射（doubao 支持的语言）
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "it": "it",
    "pt": "pt",
    "ru": "ru",
    "th": "th",
    "vi": "vi",
    "ar": "ar",
    "cs": "cs",
    "da": "da",
    "fi": "fi",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "ms": "ms",
    "nl": "nl",
    "pl": "pl",
    "ro": "ro",
    "sv": "sv",
    "tr": "tr",
    "uk": "uk",
    
    # 挪威语特殊映射
    "no": "nb",          # 挪威语 -> 挪威布克莫尔语
}

# Doubao 支持的所有语言代码集合（用于快速检查）
DOUBAO_SUPPORTED_LANGS = {
    "zh", "zh-Hant", "en", "ja", "ko", "de", "fr", "es", "it", "pt",
    "ru", "th", "vi", "ar", "cs", "da", "fi", "hr", "hu", "id",
    "ms", "nb", "nl", "pl", "ro", "sv", "tr", "uk", ""
}


def convert_lang_code(immersive_lang: str) -> str:
    """
    将沉浸式翻译的语言代码转换为 Doubao API 的语言代码
    如果不支持，返回 None
    """
    if not immersive_lang:
        return ""  # 空字符串 = 自动检测
    
    lang_lower = immersive_lang.lower()
    
    # 1. 先查映射表
    if lang_lower in IMMERSIVE_TO_DOUBAO_LANG:
        return IMMERSIVE_TO_DOUBAO_LANG[lang_lower]
    
    # 2. 如果 doubao 直接支持这个代码
    if lang_lower in DOUBAO_SUPPORTED_LANGS:
        return lang_lower
    
    # 3. 不支持的语言
    logger.warning(f"⚠️ 不支持的语言代码: {immersive_lang}，将使用自动检测")
    return ""  # 降级为自动检测


class DoubaoServer:
    """豆包翻译API服务器"""
    
    def __init__(self, config: TranslatorConfig):
        self.config = config
        self.translator: Optional[AsyncTranslator] = None
        
        # [新增] Server层并发控制 - 防止过载
        # 快车道模型 (DeepSeek, Doubao Pro): RPM=30000 → 500并发
        # 慢车道会在Client层自动处理 (seed-translation: 80并发)
        self.request_semaphore = asyncio.Semaphore(500)
        
        # [修复 2] 使用 lifespan 管理生命周期
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动时初始化
            logger.info("初始化翻译器连接池...")
            self.translator = AsyncTranslator(self.config)
            logger.info(f"🚀 Server并发限制: 500 (快车道), Client层会自动区分慢车道(80)")
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
        
        # ========== 沉浸式翻译专用端点 ==========
        @self.app.post("/translate", summary="沉浸式翻译专用接口")
        @self.app.post("/translate/", include_in_schema=False)  # 同时支持带斜杠的路径
        async def immersive_translate(request: Request):
            """
            沉浸式翻译插件的自定义翻译服务接口
            请求格式: {"source_lang": "en", "target_lang": "zh", "text_list": ["hello", "world"]}
            响应格式: {"translations": [{"detected_source_lang": "en", "text": "你好"}, ...]}
            """
            async with self.request_semaphore:
                # 获取原始 JSON 数据
                try:
                    body = await request.json()
                except Exception as e:
                    logger.error(f"[沉浸式翻译] JSON解析失败: {e}")
                    return {"translations": []}
                
                logger.debug(f"[沉浸式翻译] 原始请求: {json.dumps(body, ensure_ascii=False)[:200]}")
                
                # 灵活提取字段 (兼容不同的字段名)
                raw_source_lang = body.get("source_lang") or body.get("source_language") or body.get("from") or "auto"
                raw_target_lang = body.get("target_lang") or body.get("target_language") or body.get("to") or "zh-CN"
                text_list = body.get("text_list") or body.get("texts") or body.get("text") or []
                
                # 🔄 语言代码转换：沉浸式翻译 -> Doubao API
                source_lang = convert_lang_code(raw_source_lang)
                target_lang = convert_lang_code(raw_target_lang)
                
                # 如果 text 是单个字符串，转为列表
                if isinstance(text_list, str):
                    text_list = [text_list]
                
                if not text_list:
                    logger.warning(f"[沉浸式翻译] 空文本列表，原始body: {body}")
                    return {"translations": []}
                
                # 确保 translator 存在
                if not self.translator:
                    self.translator = AsyncTranslator(self.config)
                
                try:
                    start_time = time.time()
                    logger.info(f"┌─ [沉浸式翻译] 开始 ───────────────────────────────")
                    logger.info(f"│ 条数: {len(text_list)}, 语言: {raw_source_lang}({source_lang}) → {raw_target_lang}({target_lang})")
                    
                    results = await self.translator.translate_batch(
                        texts=text_list,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    
                    duration = time.time() - start_time
                    
                    # 构造响应并打印详细对照
                    translations = []
                    logger.info(f"├─ 翻译结果对照 ─────────────────────────────────────")
                    for i, translated in enumerate(results):
                        original = text_list[i]
                        final_text = translated if translated != "[TRANSLATION_FAILED]" else original
                        
                        # 截断过长文本用于显示（保留完整内容到日志文件）
                        orig_display = original[:60] + '...' if len(original) > 60 else original
                        trans_display = final_text[:60] + '...' if len(final_text) > 60 else final_text
                        
                        # 控制台显示简化版
                        logger.info(f"│ [{i+1:02d}] {orig_display}")
                        logger.info(f"│  →  {trans_display}")
                        
                        # 完整版记录到DEBUG级别（会写入文件）
                        logger.debug(f"│ [{i+1:02d}] 原文: {original}")
                        logger.debug(f"│ [{i+1:02d}] 译文: {final_text}")
                        
                        translations.append({
                            "detected_source_lang": raw_source_lang if raw_source_lang != "auto" else "auto",
                            "text": final_text
                        })
                    
                    logger.info(f"└─ 完成 ({duration:.2f}s) ─────────────────────────────────")
                    
                    return {"translations": translations}
                    
                except Exception as e:
                    logger.error(f"[沉浸式翻译] 翻译失败: {e}")
                    logger.error(traceback.format_exc())
                    # 返回原文作为降级
                    return {
                        "translations": [
                            {"detected_source_lang": "error", "text": t} 
                            for t in text_list
                        ]
                    }
        
        @self.app.post("/v1/chat/completions")
        async def create_chat_completion(raw_request: Request):
            # [新增] 使用semaphore控制并发
            async with self.request_semaphore:
                # 获取原始 JSON 数据用于调试
                try:
                    body = await raw_request.json()
                except Exception as e:
                    logger.error(f"JSON解析失败: {e}")
                    raise HTTPException(status_code=400, detail="Invalid JSON")
                
                logger.debug(f"[OpenAI] 原始请求: {json.dumps(body, ensure_ascii=False)[:200]}")
                
                model = body.get("model", "doubao-seed-translation-250915")
                messages = body.get("messages", [])
                
                # 心跳检测
                if not messages:
                    logger.info("空消息列表，返回心跳成功")
                    return {
                        "id": "test-conn", 
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "choices": [{"index":0, "message":{"role":"assistant", "content":"OK"}, "finish_reason":"stop"}]
                    }
                
                # 智能提取用户消息
                user_msg = None
                for m in reversed(messages):
                    if m.get("role") == "user":
                        content = m.get("content")
                        if isinstance(content, str):
                            user_msg = content
                        elif isinstance(content, list):
                            # 处理数组格式
                            texts = []
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    texts.append(item["text"])
                                elif isinstance(item, str):
                                    texts.append(item)
                            user_msg = " ".join(texts)
                        if user_msg:
                            break
                
                if not user_msg:
                    logger.warning(f"未找到有效用户消息，原始消息: {messages}")
                    raise HTTPException(status_code=400, detail="未找到用户消息")
                
                # [修复 3] 确保 translator 存在 (lifespan 有时在测试环境可能没触发)
                if not self.translator:
                     self.translator = AsyncTranslator(self.config)
                
                try:
                    # 执行翻译
                    # 灵活提取语言参数
                    source_lang = body.get("source_language") or body.get("source_lang") or "auto"
                    target_lang = body.get("target_language") or body.get("target_lang") or "zh"
                    
                    start_time = time.time()
                    logger.info(f"┌─ [OpenAI接口] 开始 ─────────────────────────────────")
                    logger.info(f"│ 字符数: {len(user_msg)}, 语言: {source_lang} → {target_lang}")
                    
                    results = await self.translator.translate_batch(
                        texts=[user_msg],
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    duration = time.time() - start_time
                    
                    translated_text = results[0] if results else ""
                    
                    # 检查是否翻译失败
                    if translated_text == "[TRANSLATION_FAILED]":
                        logger.error("│ ❌ 翻译失败")
                        logger.error(f"└─────────────────────────────────────────────────────")
                        raise HTTPException(status_code=502, detail="Upstream Translation Failed")

                    # 打印原文和译文对照
                    orig_display = user_msg[:80] + '...' if len(user_msg) > 80 else user_msg
                    trans_display = translated_text[:80] + '...' if len(translated_text) > 80 else translated_text
                    
                    logger.info(f"│ 原文: {orig_display}")
                    logger.info(f"│ 译文: {trans_display}")
                    logger.info(f"└─ 完成 ({duration:.2f}s, {len(user_msg)} → {len(translated_text)} 字符) ────")
                    
                    # 完整版写入日志文件
                    logger.debug(f"[OpenAI] 完整原文: {user_msg}")
                    logger.debug(f"[OpenAI] 完整译文: {translated_text}")
                    
                    return {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
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
    # 初始化日志系统
    log_file = setup_logging(debug=debug)
    
    if not api_key:
        api_key = os.getenv("ARK_API_KEY")
        if not api_key:
            logger.error("错误: 未提供 API Key")
            return
    
    logger.info("═" * 60)
    logger.info("🚀 豆包翻译API服务器启动")
    logger.info(f"📍 地址: http://{host}:{port}")
    logger.info(f"📝 日志文件: {log_file}")
    logger.info("═" * 60)
            
    # [修复] 使用 from_args 以加载 models.json 和环境变量配置
    config = TranslatorConfig.from_args(api_key=api_key)
    server = DoubaoServer(config)
    server.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server()