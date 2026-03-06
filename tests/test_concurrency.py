#!/usr/bin/env python3
"""
并发性能测试脚本
测试 doubao-seed-translation-250915 模型在不同并发下的表现
"""

import asyncio
import httpx
import time
from typing import List

async def perform_translation(client: httpx.AsyncClient, text: str, test_id: int) -> dict:
    """发送单个翻译请求"""
    start_time = time.time()
    try:
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "doubao-seed-translation-250915",
                "messages": [{"role": "user", "content": text}],
                "target_language": "zh"
            },
            timeout=30.0
        )
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            return {
                "id": test_id,
                "status": "success",
                "duration": duration,
                "input_length": len(text),
                "output_length": len(data["choices"][0]["message"]["content"])
            }
        else:
            return {
                "id": test_id,
                "status": "failed",
                "duration": duration,
                "error": response.status_code
            }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "id": test_id,
            "status": "error",
            "duration": duration,
            "error": str(e)
        }

async def run_concurrency_test(num_requests: int = 100, concurrency: int = 80):
    """运行并发测试"""
    print(f"\n{'='*60}")
    print(f"🚀 并发性能测试")
    print(f"{'='*60}")
    print(f"总请求数: {num_requests}")
    print(f"并发数: {concurrency}")
    print(f"{'='*60}\n")
    
    # 准备测试文本（不同长度）
    test_texts = [
        "Hello",  # 短文本
        "Hello, how are you today?",  # 中等文本
        "The quick brown fox jumps over the lazy dog. " * 5,  # 长文本
    ]
    
    # 创建请求列表
    requests = []
    for i in range(num_requests):
        text = test_texts[i % len(test_texts)]
        requests.append((i, text))
    
    # 使用httpx连接池
    async with httpx.AsyncClient() as client:
        # 使用Semaphore控制并发
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_test(test_id: int, text: str):
            async with semaphore:
                return await perform_translation(client, text, test_id)
        
        # 开始测试
        start_time = time.time()
        print(f"⏱️  开始时间: {time.strftime('%H:%M:%S')}")
        
        results = await asyncio.gather(
            *[limited_test(test_id, text) for test_id, text in requests]
        )
        
        total_duration = time.time() - start_time
        
    # 统计结果
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    success_results = [r for r in results if r["status"] == "success"]
    avg_duration = sum(r["duration"] for r in success_results) / len(success_results) if success_results else 0
    
    print(f"\n{'='*60}")
    print(f"📊 测试结果")
    print(f"{'='*60}")
    print(f"✅ 成功: {success_count}/{num_requests} ({success_count/num_requests*100:.1f}%)")
    print(f"❌ 失败: {failed_count}")
    print(f"⚠️  错误: {error_count}")
    print(f"{'='*60}")
    print(f"⏱️  总耗时: {total_duration:.2f}s")
    print(f"📈 吞吐量: {num_requests/total_duration:.2f} req/s")
    print(f"⏱️  平均响应时间: {avg_duration:.2f}s")
    print(f"{'='*60}\n")
    
    # 显示错误详情
    if failed_count > 0 or error_count > 0:
        print("\n❌ 错误详情:")
        for r in results:
            if r["status"] != "success":
                print(f"  [{r['id']}] {r['status']}: {r.get('error', 'Unknown')}")

async def main():
    """主函数"""
    print("\n" + "="*60)
    print("🎯 doubao-seed-translation-250915 并发性能测试")
    print("="*60)
    
    # 确保服务器正在运行
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/", timeout=5.0)
            if response.status_code != 200:
                print("❌ 服务器未运行，请先启动: python main.py server --port 8000")
                return
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请先启动服务器: python main.py server --port 8000")
        return
    
    print("✅ 服务器连接正常\n")
    
    # 测试不同并发级别
    test_configs = [
        (50, 20, "低并发"),
        (100, 50, "中等并发"),
        (100, 80, "高并发（优化后）"),
    ]
    
    for num_requests, concurrency, desc in test_configs:
        print(f"\n📍 测试场景: {desc}")
        await run_concurrency_test(num_requests, concurrency)
        await asyncio.sleep(2)  # 间隔2秒避免过载

if __name__ == "__main__":
    asyncio.run(main())
