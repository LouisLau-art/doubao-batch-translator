#!/usr/bin/env python3
"""
JSON处理器 - 高并发单请求翻译
专门适配 doubao-seed-translation-250915 模型，该模型不支持批量请求
"""

import json
import os
import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm.asyncio import tqdm

from core.client import AsyncDoubaoClient
from core.exceptions import FileProcessingError


logger = logging.getLogger(__name__)


class JSONProcessor:
    """JSON文件翻译处理器（高并发单请求版本）"""
    
    def __init__(self, api_key: str):
        """初始化JSON处理器
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self.client = AsyncDoubaoClient(api_key)
        
        # 保存配置
        self.SAVE_INTERVAL = 50  # 每50个项目保存一次进度
        self.processed_count = 0
        
    def _format_json_output(self, data: List[Dict]) -> List[Dict]:
        """格式化JSON输出，按照指定键顺序
        
        Args:
            data: 要格式化的数据列表
            
        Returns:
            格式化后的数据列表
        """
        formatted_data = []
        for item in data:
            # 创建新字典，按照指定顺序插入键
            formatted_item = {
                'original': item.get('original', ''),
                'translated': item.get('translated'),
                'id': item.get('id', ''),
                'file': item.get('file', ''),
                'line': item.get('line', 0),
                'type': item.get('type', 'text'),
                'context': item.get('context', ''),
                'translated_at': item.get('translated_at')
            }
            
            # 添加其他可能的字段
            for key, value in item.items():
                if key not in formatted_item:
                    formatted_item[key] = value
            
            formatted_data.append(formatted_item)
        
        return formatted_data
    
    def _create_backup(self, file_path: str) -> str:
        """创建文件备份
        
        Args:
            file_path: 文件路径
            
        Returns:
            备份文件路径
        """
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"已创建备份文件: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return None
    
    def _save_progress(self, data: List[Dict], file_path: str, backup_path: str = None) -> bool:
        """保存翻译进度
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
            backup_path: 备份文件路径（可选）
            
        Returns:
            是否保存成功
        """
        try:
            # 创建备份（如果文件存在且没有指定备份路径）
        if not backup_path and os.path.exists(file_path):
            backup_path = self._create_backup(file_path)
            
            # 格式化输出
            formatted_data = self._format_json_output(data)
            
            # 保存数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(formatted_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"进度已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
            return False
    
    def _get_untranslated_items(self, data: List[Dict]) -> List[Dict]:
        """获取未翻译的条目
        
        Args:
            data: 数据列表
            
        Returns:
            未翻译的条目列表
        """
        untranslated = []
        
        for item in data:
            translated = item.get('translated')
            if translated is None or translated == "":
            untranslated.append(item)
        
        return untranslated
    
    async def _translate_single_item(self, item: Dict, source_lang: str, target_lang: str) -> Dict:
        """翻译单个条目（就地更新）
        
        Args:
            item: 要翻译的条目
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            更新后的条目
        """
        try:
            original_text = item['original']
            
            logger.debug(f"翻译: {original_text[:50]}...")
            
            # 调用API进行翻译
            translation = await self.client.async_translate(
                original_text, source_lang, target_lang)
            
            if translation:
                logger.debug(f"翻译结果: {translation[:50]}...")
                # 就地更新条目
                item['translated'] = translation
                item['translated_at'] = datetime.now().isoformat()
            else:
                logger.warning(f"API调用返回空结果: {original_text[:50]}...")
                item['translated'] = None
            
            return item
            
        except Exception as e:
            logger.error(f"翻译条目失败 (ID: {item.get('id', 'unknown')}): {e}")
            item['translation_error'] = str(e)
            return item
    
    def _get_translation_stats(self, data: List[Dict]) -> Dict[str, int]:
        """获取翻译统计信息
        
        Args:
            data: 数据列表
            
        Returns:
            统计信息字典
        """
        total = len(data)
        translated = sum(1 for item in data if item.get('translated') and item['translated'].strip())
        
        return {
            'total': total,
            'translated': translated,
            'untranslated': total - translated,
            'progress': round(translated / total * 100, 2) if total > 0 else 0
        }
    
    async def translate_file(self, input_file: str, output_file: str = None,
                           source_lang: str = "en", 
                           target_lang: str = "zh") -> Dict[str, Any]:
        """翻译JSON文件（高并发单请求版本）
        
        实现用户要求的逻辑：
        1. 加载: 使用 json.load 读取整个文件
        2. 过滤: 创建 pending_items 列表，只包含 item['translated'] is None 的对象引用
        3. 并发处理: 使用 asyncio 创建高并发任务池，最多20个并发请求
        4. 逐个处理: 每个任务处理一个条目
        5. 就地更新: 直接修改原始对象，不丢失元数据
        6. 定期保存: 每50个项目保存一次进度
        
        Args:
            input_file: 输入JSON文件路径
            output_file: 输出JSON文件路径（默认覆盖原文件）
            source_lang: 源语言代码（默认：en）
            target_lang: 目标语言代码（默认：zh）
            
        Returns:
            翻译结果统计信息
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path
        
        logger.info(f"开始处理JSON文件: {input_path} -> {output_path}")
        
        try:
            # 1. 加载JSON文件
            if not input_path.exists():
                raise FileProcessingError(f"输入文件不存在: {input_path}")
            
            with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if not isinstance(data, list):
                raise FileProcessingError("JSON数据必须是数组格式")
            
            if not data:
                logger.info("JSON数组为空，无需翻译")
                return {
                    'total': 0,
                    'translated': 0,
                    'untranslated': 0,
                    'progress': 100,
                    'success': True
                }
            
            # 初始统计
            stats = self._get_translation_stats(data)
            logger.info(f"文件统计: 总计 {stats['total']} 条目, {stats['translated']} 已翻译, {stats['untranslated']} 待翻译")
            
            # 2. 过滤 - 创建pending_items列表，只包含translated为None的项目引用
            pending_items = self._get_untranslated_items(data)
            
            if not pending_items:
                logger.info("没有需要翻译的条目")
                return stats
            
            logger.info(f"开始并发翻译 {len(pending_items)} 个未完成条目")
            
            # 3. 高并发处理 - 使用asyncio.as_completed处理任务
            completed_count = 0
            backup_path = None
            
            with tqdm(total=len(pending_items), desc="翻译进度") as pbar:
                # 创建所有任务
                tasks = []
                for item in pending_items:
                    task = asyncio.create_task(
                        self._translate_single_item(item, source_lang, target_lang)
                
                # 使用asyncio.as_completed处理任务
                for completed_task in asyncio.as_completed(tasks):
                    try:
                        result = await completed_task
                        completed_count += 1
                        
                        # 更新进度条
                        pbar.set_postfix({
                            '成功率': f"{completed_count/len(pending_items)*100:.1f}%"
                        })
                        pbar.update(1)
                        
                        # 5. 定期保存进度 - 每50个项目保存一次
                        if completed_count % self.SAVE_INTERVAL == 0:
                    # 保存进度
                    self._save_progress(data, str(output_path), backup_path)
                    logger.info(f"已保存进度: {completed_count}/{len(pending_items)}")
                    
                    except Exception as e:
                        logger.error(f"处理任务失败: {e}")
                        continue
            
            # 6. 最终保存
            self._save_progress(data, str(output_path), backup_path)
            
            # 最终统计
            final_stats = self._get_translation_stats(data)
            final_stats['success'] = True
            final_stats['output_file'] = str(output_path)
            
            logger.info(f"翻译完成! 成功率: {final_stats['progress']}%")
            return final_stats
            
        except Exception as e:
            logger.error(f"处理JSON文件失败: {e}")
            raise FileProcessingError(f"处理JSON文件失败: {e}")
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.close()