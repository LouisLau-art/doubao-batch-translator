#!/usr/bin/env python3
"""
JSON处理器 - RenPy翻译专用
专门处理包含翻译数据的JSON文件，支持断点续传和进度保存
"""

import json
import os
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from core import AsyncTranslator, TranslatorConfig, ValidationError
from core.exceptions import FileProcessingError


logger = logging.getLogger(__name__)


class JSONProcessor:
    """JSON文件翻译处理器（RenPy翻译专用）"""
    
    def __init__(self, translator: AsyncTranslator):
        """初始化JSON处理器
        
        Args:
            translator: 异步翻译器实例
        """
        self.translator = translator
        
        # 支持的字段配置
        self.supported_fields = {
            'id': '翻译条目ID',
            'file': '源文件路径',
            'line': '文件行号',
            'type': '文本类型',
            'original': '原始文本',
            'translated': '翻译文本',
            'context': '上下文信息',
            'translated_at': '翻译时间'
        }
    
    def _validate_json_structure(self, data: Any) -> List[Dict]:
        """验证JSON数据结构
        
        Args:
            data: JSON数据
            
        Returns:
            验证后的条目列表
            
        Raises:
            ValidationError: 数据结构验证失败
        """
        if not isinstance(data, list):
            raise ValidationError("JSON数据必须是数组格式")
        
        if not data:
            raise ValidationError("JSON数组不能为空")
        
        validated_items = []
        
        for i, item in enumerate(data):
            try:
                if not isinstance(item, dict):
                    raise ValidationError(f"项目 {i} 不是字典类型")
                
                # 验证必需字段
                required_fields = ['original']
                missing_fields = [field for field in required_fields if field not in item]
                if missing_fields:
                    raise ValidationError(f"项目 {i} 缺少必需字段: {missing_fields}")
                
                # 清理和标准化数据
                cleaned_item = {
                    'original': str(item['original']).strip(),
                    'translated': None,
                    'id': item.get('id', f"item_{i}"),
                    'file': item.get('file', ''),
                    'line': item.get('line', 0),
                    'type': item.get('type', 'text'),
                    'context': item.get('context', ''),
                    'translated_at': item.get('translated_at')
                }
                
                # 如果已有翻译，保留
                if item.get('translated') is not None:
                    cleaned_item['translated'] = str(item['translated']).strip()
                
                # 过滤空文本
                if not cleaned_item['original']:
                    logger.warning(f"跳过项目 {i}：原始文本为空")
                    continue
                
                validated_items.append(cleaned_item)
                
            except Exception as e:
                logger.warning(f"验证项目 {i} 失败: {e}")
                continue
        
        if not validated_items:
            raise ValidationError("没有有效的翻译条目")
        
        logger.info(f"验证了 {len(validated_items)} 个有效条目")
        return validated_items
    
    def _create_backup(self, file_path: str) -> str:
        """创建文件备份
        
        Args:
            file_path: 文件路径
            
        Returns:
            备份文件路径
        """
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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
            if not backup_path:
                backup_path = self._create_backup(file_path)
            
            # 保存数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"进度已保存到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
            return False
    
    def _filter_untranslated_items(self, data: List[Dict]) -> List[Dict]:
        """过滤出未翻译的条目
        
        Args:
            data: 数据列表
            
        Returns:
            未翻译的条目列表
        """
        untranslated = []
        
        for item in data:
            # 检查是否需要翻译
            translated = item.get('translated')
            if translated is None or translated == "":
                untranslated.append(item)
        
        return untranslated
    
    def _get_translation_stats(self, data: List[Dict]) -> Dict[str, int]:
        """获取翻译统计信息
        
        Args:
            data: 数据列表
            
        Returns:
            统计信息字典
        """
        total = len(data)
        translated = sum(1 for item in data if item.get('translated'))
        untranslated = total - translated
        
        return {
            'total': total,
            'translated': translated,
            'untranslated': untranslated,
            'progress': round(translated / total * 100, 2) if total > 0 else 0
        }
    
    async def _progress_callback(self, progress: float, message: str, 
                                stats_callback: Optional[Callable] = None):
        """进度回调函数
        
        Args:
            progress: 进度百分比（0-1）
            message: 进度消息
            stats_callback: 统计信息回调
        """
        if stats_callback:
            stats = stats_callback()
            logger.info(f"进度: {progress:.1%} - {message} (统计: {stats['translated']}/{stats['total']} 已完成)")
        else:
            logger.info(f"进度: {progress:.1%} - {message}")
    
    async def translate_file(self, input_file: str, output_file: str = None,
                           source_lang: Optional[str] = None, 
                           target_lang: str = "zh",
                           batch_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """翻译JSON文件
        
        Args:
            input_file: 输入JSON文件路径
            output_file: 输出JSON文件路径（默认覆盖原文件）
            source_lang: 源语言代码（可选）
            target_lang: 目标语言代码（必选）
            batch_callback: 批次完成回调函数
            
        Returns:
            翻译结果统计信息
        """
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path
        
        logger.info(f"开始处理JSON文件: {input_path} -> {output_path}")
        
        try:
            # 验证文件存在
            if not input_path.exists():
                raise FileProcessingError(f"输入文件不存在: {input_path}")
            
            # 读取和验证JSON数据
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            data = self._validate_json_structure(raw_data)
            
            # 获取统计信息
            stats = self._get_translation_stats(data)
            logger.info(f"文件统计: 总计 {stats['total']} 条目, {stats['translated']} 已翻译, {stats['untranslated']} 待翻译")
            
            if stats['untranslated'] == 0:
                logger.info("没有需要翻译的条目")
                return stats
            
            # 过滤未翻译条目
            untranslated_items = self._filter_untranslated_items(data)
            logger.info(f"开始翻译 {len(untranslated_items)} 个未完成条目")
            
            # 创建批次回调
            async def batch_progress_callback(progress: float, message: str):
                if batch_callback:
                    await batch_callback(progress, message)
                await self._progress_callback(progress, message, lambda: stats)
            
            # 提取需要翻译的文本
            texts = [item['original'] for item in untranslated_items]
            
            # 执行翻译
            try:
                translation_results = await self.translator.translate_batch(
                    texts=texts,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    progress_callback=batch_progress_callback
                )
                
                # 回填翻译结果
                result_index = 0
                for i, item in enumerate(data):
                    if item.get('translated') is None or item.get('translated') == "":
                        if result_index < len(translation_results):
                            item['translated'] = translation_results[result_index]['translated']
                            item['translated_at'] = datetime.now().isoformat()
                            result_index += 1
                
                # 保存结果
                success = self._save_progress(data, str(output_path))
                
                if success:
                    # 更新统计信息
                    final_stats = self._get_translation_stats(data)
                    final_stats['success'] = True
                    final_stats['output_file'] = str(output_path)
                    
                    logger.info(f"翻译完成! 成功率: {final_stats['progress']}%")
                    return final_stats
                else:
                    raise FileProcessingError("保存翻译结果失败")
                
            except Exception as e:
                logger.error(f"翻译过程失败: {e}")
                # 尝试保存当前进度
                self._save_progress(data, str(output_path))
                raise
            
        except Exception as e:
            logger.error(f"处理JSON文件失败: {e}")
            raise FileProcessingError(f"处理JSON文件失败: {e}")
    
    async def check_status(self, input_file: str) -> Dict[str, Any]:
        """检查JSON文件的翻译状态
        
        Args:
            input_file: JSON文件路径
            
        Returns:
            状态信息
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data = self._validate_json_structure(data)
            stats = self._get_translation_stats(data)
            
            return {
                'file': str(input_file),
                'exists': True,
                'stats': stats,
                'status': 'completed' if stats['untranslated'] == 0 else 'incomplete'
            }
            
        except Exception as e:
            return {
                'file': str(input_file),
                'exists': os.path.exists(input_file),
                'error': str(e),
                'status': 'error'
            }