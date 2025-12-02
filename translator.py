#!/usr/bin/env python3
"""
JSON翻译工具 - 异步批量翻译脚本
支持断点续传、批处理、并发控制、进度显示等功能
"""

import json
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from tqdm.asyncio import tqdm
import hashlib


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatchTranslator:
    """异步批量翻译器"""
    
    def __init__(self, api_key: str, max_concurrent: int = 5, max_requests_per_second: float = 50.0):
        self.api_key = api_key
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/responses"
        self.model = "doubao-seed-translation-250915"
        self.max_concurrent = max_concurrent
        self.max_requests_per_second = max_requests_per_second
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_times = []
        
        # HTTP客户端配置
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def rate_limit(self):
        """请求频率限制"""
        now = datetime.now()
        # 移除1秒前的请求记录
        self.request_times = [t for t in self.request_times if (now - t).total_seconds() < 1]
        
        # 如果超过限制，等待
        if len(self.request_times) >= self.max_requests_per_second:
            sleep_time = 1 - (now - min(self.request_times)).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.request_times.append(now)
    
    def create_batch_payload(self, batch_items: List[Dict]) -> Dict:
        """创建批处理请求载荷"""
        input_array = []
        
        for item in batch_items:
            input_item = {
                "id": item["id"],
                "text": item["original"],
                "source_language": "en", 
                "target_language": "zh"
            }
            
            # 添加上下文信息（如果存在）
            if item.get("context"):
                input_item["context"] = item["context"]
            
            input_array.append(input_item)
        
        payload = {
            "model": self.model,
            "input": input_array,
            "response_format": {"type": "json_object"}
        }
        
        return payload
    
    async def translate_batch(self, batch_items: List[Dict]) -> List[Dict]:
        """翻译一批文本"""
        await self.rate_limit()
        
        async with self.semaphore:
            payload = self.create_batch_payload(batch_items)
            
            for attempt in range(3):  # 最多重试3次
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            self.api_url,
                            headers=self.headers,
                            json=payload
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            return self.parse_batch_response(result, batch_items)
                        else:
                            logger.error(f"API请求失败: {response.status_code} - {response.text}")
                            if attempt == 2:
                                raise Exception(f"API请求最终失败: {response.status_code}")
                            
                except httpx.TimeoutException:
                    logger.warning(f"请求超时，重试 {attempt + 1}/3")
                    if attempt == 2:
                        raise Exception("请求最终超时")
                except Exception as e:
                    logger.error(f"翻译批次时出错: {e}")
                    if attempt == 2:
                        raise
            
            return []  # 如果所有重试都失败，返回空列表
    
    def parse_batch_response(self, api_response: Dict, batch_items: List[Dict]) -> List[Dict]:
        """解析API响应"""
        results = []
        
        try:
            # 解析豆包API响应格式
            choices = api_response.get("choices", [])
            if not choices:
                logger.warning("API响应中没有choices")
                return []
            
            response_content = choices[0].get("message", {}).get("content", "{}")
            
            # 尝试解析JSON响应
            try:
                parsed_content = json.loads(response_content)
            except json.JSONDecodeError:
                logger.error(f"无法解析API响应JSON: {response_content}")
                return []
            
            # 提取翻译结果
            translations = parsed_content.get("translations", [])
            
            if len(translations) != len(batch_items):
                logger.warning(f"翻译结果数量不匹配: 期望 {len(batch_items)}, 实际 {len(translations)}")
                # 填充缺失的翻译结果
                while len(translations) < len(batch_items):
                    translations.append("")
            
            for i, item in enumerate(batch_items):
                translated_text = translations[i] if i < len(translations) else ""
                
                result = {
                    "id": item["id"],
                    "file": item["file"],
                    "line": item["line"],
                    "type": item["type"],
                    "original": item["original"],
                    "translated": translated_text,
                    "context": item.get("context"),
                    "translated_at": datetime.now().isoformat()
                }
                results.append(result)
                
        except Exception as e:
            logger.error(f"解析API响应时出错: {e}")
            # 返回原始条目，但标记为翻译失败
            for item in batch_items:
                result = item.copy()
                result["translated"] = ""
                result["translated_at"] = datetime.now().isoformat()
                results.append(result)
        
        return results
    
    def create_optimal_batch(self, items: List[Dict], max_chars: int = 500, max_items: int = 15) -> List[List[Dict]]:
        """创建最优批次，考虑字符数和条目数限制"""
        batches = []
        current_batch = []
        current_chars = 0
        
        for item in items:
            item_chars = len(item["original"])
            
            # 检查是否需要开始新批次
            if (current_batch and 
                (current_chars + item_chars > max_chars or 
                 len(current_batch) >= max_items)):
                
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
            
            current_batch.append(item)
            current_chars += item_chars
        
        # 添加最后一个批次
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def translate_all(self, data: List[Dict], progress_callback=None) -> List[Dict]:
        """翻译所有未完成的条目"""
        # 过滤出需要翻译的条目
        untranslated_items = [item for item in data if not item.get("translated")]
        
        if not untranslated_items:
            logger.info("没有需要翻译的条目")
            return data
        
        logger.info(f"找到 {len(untranslated_items)} 个需要翻译的条目")
        
        # 创建批次
        batches = self.create_optimal_batch(untranslated_items)
        logger.info(f"创建了 {len(batches)} 个批次")
        
        # 翻译所有批次
        all_results = []
        
        with tqdm(total=len(batches), desc="翻译进度") as pbar:
            for i, batch in enumerate(batches):
                try:
                    logger.info(f"处理批次 {i+1}/{len(batches)} (包含 {len(batch)} 个条目)")
                    
                    batch_results = await self.translate_batch(batch)
                    all_results.extend(batch_results)
                    
                    # 更新原始数据
                    for result in batch_results:
                        for original_item in data:
                            if original_item["id"] == result["id"]:
                                original_item["translated"] = result["translated"]
                                original_item["translated_at"] = result["translated_at"]
                                break
                    
                    pbar.update(1)
                    
                    # 调用进度回调
                    if progress_callback:
                        progress = (i + 1) / len(batches)
                        await progress_callback(progress, f"已完成批次 {i+1}/{len(batches)}")
                    
                    # 短暂延迟避免过载
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"处理批次 {i+1} 时出错: {e}")
                    # 为失败的批次添加空翻译结果
                    for item in batch:
                        result = item.copy()
                        result["translated"] = ""
                        result["translated_at"] = datetime.now().isoformat()
                        all_results.append(result)
        
        return data


class JsonTranslator:
    """JSON文件翻译器"""
    
    def __init__(self, input_file: str, output_file: str = None):
        self.input_file = input_file
        self.output_file = output_file or input_file
        self.backup_file = f"{input_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def load_json(self) -> List[Dict]:
        """加载JSON文件"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载文件: {self.input_file}, 包含 {len(data)} 个条目")
            return data
        except Exception as e:
            logger.error(f"加载JSON文件失败: {e}")
            raise
    
    def save_json(self, data: List[Dict]) -> None:
        """保存JSON文件（自动备份）"""
        try:
            # 创建备份
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(self.backup_file, 'w', encoding='utf-8') as f:
                    f.write(backup_data)
                logger.info(f"已创建备份文件: {self.backup_file}")
            
            # 保存新数据
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存文件: {self.output_file}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            raise
    
    async def translate(self, api_key: str):
        """执行翻译"""
        # 加载数据
        data = self.load_json()
        
        # 检查翻译器API密钥
        if not api_key:
            raise ValueError("需要提供ARK_API_KEY环境变量或通过参数指定")
        
        # 创建翻译器
        translator = BatchTranslator(api_key)
        
        # 进度回调函数
        async def progress_callback(progress: float, message: str):
            tqdm.write(f"进度: {progress:.1%} - {message}")
        
        # 执行翻译
        try:
            await translator.translate_all(data, progress_callback)
            
            # 保存结果
            self.save_json(data)
            
            logger.info("翻译完成！")
            
            # 统计结果
            translated_count = sum(1 for item in data if item.get("translated"))
            total_count = len(data)
            
            logger.info(f"统计结果: {translated_count}/{total_count} 个条目已完成翻译")
            
        except KeyboardInterrupt:
            logger.info("用户中断翻译，保存当前进度...")
            self.save_json(data)
            logger.info("进度已保存，可以稍后继续翻译")
            
        except Exception as e:
            logger.error(f"翻译过程中发生错误: {e}")
            logger.info("尝试保存当前进度...")
            self.save_json(data)
            raise


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JSON批量翻译工具')
    parser.add_argument('input_file', help='输入JSON文件路径')
    parser.add_argument('--output', '-o', help='输出JSON文件路径')
    parser.add_argument('--api-key', help='豆包API密钥（也可以通过ARK_API_KEY环境变量设置）')
    parser.add_argument('--concurrent', '-c', type=int, default=5, help='最大并发数（默认5）')
    parser.add_argument('--rps', type=float, default=50.0, help='每秒最大请求数（默认50）')
    
    args = parser.parse_args()
    
    # 获取API密钥
    api_key = args.api_key or os.getenv('ARK_API_KEY')
    if not api_key:
        print("错误: 未提供API密钥，请设置ARK_API_KEY环境变量或使用--api-key参数")
        print("示例:")
        print("  export ARK_API_KEY=your_api_key")
        print("  python translator.py translation_work.json")
        print("  或者")
        print("  python translator.py translation_work.json --api-key=your_api_key")
        return
    
    try:
        translator = JsonTranslator(args.input_file, args.output)
        await translator.translate(api_key)
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {args.input_file}")
        
    except Exception as e:
        print(f"翻译失败: {e}")
        logger.exception("翻译过程发生未处理的异常")


if __name__ == "__main__":
    asyncio.run(main())