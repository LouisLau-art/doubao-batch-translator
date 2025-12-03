#!/usr/bin/env python3
import asyncio
import os
from core.config import TranslatorConfig
from core.client import AsyncTranslator

async def test_connection():
    # 1. 加载配置
    try:
        config = TranslatorConfig.from_env()
        print(f"✅ 配置加载成功")
        print(f"   - API Key: {config.api_key[:8]}******")
        print(f"   - 并发数: {config.max_concurrent}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return

    # 2. 测试 API 连接
    print("\n🔄 正在测试 API 连接 (翻译 'Hello World')...")
    translator = AsyncTranslator(config.api_key)
    
    try:
        # 这里的 translate_batch 内部会使用我们优化过的 httpx client
        results = await translator.translate_batch(["Hello World", "This is a test."], target_lang="zh")
        
        if results and "[TRANSLATION_FAILED]" not in results:
            print(f"✅ API 测试成功!")
            print(f"   - 原文: Hello World -> 译文: {results[0]}")
            print(f"   - 原文: This is a test. -> 译文: {results[1]}")
        else:
            print(f"❌ API 返回了错误结果: {results}")
            
    except Exception as e:
        print(f"❌ API 连接失败: {e}")
    finally:
        await translator.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
