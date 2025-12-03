#!/usr/bin/env python3
"""
JSON处理器 - 高并发单请求翻译
专门适配 doubao-seed-translation-250915 模型
"""

import json
import os
import asyncio
import logging
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# [修改 1] 移除 tqdm，使用标准日志
# from tqdm.asyncio import tqdm

from core.client import AsyncTranslator
from core.exceptions import FileProcessingError

logger = logging.getLogger(__name__)

# process_tags 函数保持不变 (非常棒的正则逻辑)
def process_tags(text):
    text = text.strip()
    if not text: return "", "", ""
    prefix = ""
    suffix = ""
    while True:
        start_match = re.match(r"^(\{[a-zA-Z]+(=[^}]+)?\})", text)
        end_match = re.search(r"(\{[/\a-zA-Z]+\})$", text)
        if start_match and end_match:
            start_tag = start_match.group(1)
            end_tag = end_match.group(1)
            start_type = start_tag.strip('{}').split('=')[0]
            end_type = end_tag.strip('{/}') if end_tag.startswith('{/') else None
            if end_type and start_type == end_type:
                middle_text = text[len(start_tag):-len(end_tag)]
                if start_tag not in middle_text:
                    prefix += start_tag
                    suffix = end_tag + suffix
                    text = middle_text
                    continue
        break
    return prefix, text, suffix


class JSONProcessor:
    """JSON文件翻译处理器"""
    
    def __init__(self, translator: AsyncTranslator):
        self.translator = translator
        self.SAVE_INTERVAL = 50
        
    def _format_json_output(self, data: List[Dict]) -> List[Dict]:
        """格式化输出，保持原有结构"""
        # 如果原数据有特定的字段顺序需求，可以在这里处理
        # 目前简单返回即可，因为 dict 在 Py3.7+ 是有序的
        return data 
    
    def _create_backup(self, file_path: str) -> str:
        if not os.path.exists(file_path): return None
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup.{timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception:
            return None
    
    def _save_progress(self, data: List[Dict], file_path: str, backup_path: str = None) -> bool:
        try:
            # 只有第一次保存时创建备份
            if not backup_path and os.path.exists(file_path) and not hasattr(self, '_has_backed_up'):
                backup_path = self._create_backup(file_path)
                self._has_backed_up = True
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
            return False
    
    def _get_untranslated_items(self, data: List[Dict]) -> List[Dict]:
        return [item for item in data if not item.get('translated')]
    
    def _get_translation_stats(self, data: List[Dict]) -> Dict[str, int]:
        total = len(data)
        translated = sum(1 for item in data if item.get('translated'))
        return {
            'total': total,
            'translated': translated,
            'untranslated': total - translated,
            'progress': round(translated / total * 100, 2) if total > 0 else 0
        }
    
    async def translate_file(self, input_file: str, output_file: str = None,
                           source_lang: str = "en", 
                           target_lang: str = "zh") -> Dict[str, Any]:
        """翻译JSON文件核心逻辑"""
        input_path = Path(input_file)
        output_path = Path(output_file) if output_file else input_path
        
        logger.info(f"处理JSON: {input_path}")
        
        try:
            if not input_path.exists():
                raise FileProcessingError(f"文件不存在: {input_path}")
            
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise FileProcessingError("JSON必须是数组格式")
            
            # 初始统计
            stats = self._get_translation_stats(data)
            logger.info(f"进度: {stats['translated']}/{stats['total']} ({stats['progress']}%)")
            
            # 获取待翻译项
            pending_items = self._get_untranslated_items(data)
            if not pending_items:
                logger.info("无需翻译")
                return {**stats, 'success': True}
            
            logger.info(f"开始翻译 {len(pending_items)} 个条目...")
            
            # 分批处理
            batch_size = 50
            batches = [pending_items[i:i+batch_size] for i in range(0, len(pending_items), batch_size)]
            total_batches = len(batches)
            completed_count = 0
            
            for batch_idx, batch in enumerate(batches):
                try:
                    # 1. 预处理：分离标签
                    core_texts = []
                    tag_infos = []
                    for item in batch:
                        orig = item.get('original', '')
                        prefix, core, suffix = process_tags(orig)
                        core_texts.append(core)
                        tag_infos.append((prefix, suffix))
                    
                    # 2. 批量翻译 (并发)
                    # [关键] 过滤掉空文本不翻译，节省 Token
                    indices_to_translate = [i for i, t in enumerate(core_texts) if t.strip()]
                    texts_to_translate = [core_texts[i] for i in indices_to_translate]
                    
                    if texts_to_translate:
                        translated_results = await self.translator.translate_batch(
                            texts_to_translate, source_lang, target_lang
                        )
                        
                        # 回填结果
                        trans_map = dict(zip(indices_to_translate, translated_results))
                        
                        for i, item in enumerate(batch):
                            prefix, suffix = tag_infos[i]
                            trans_text = trans_map.get(i, "") # 如果原本是空或翻译失败
                            
                            if trans_text == "[TRANSLATION_FAILED]":
                                # 失败时保留原文逻辑
                                # 这里可以选择保留空，或者填入原文，看需求
                                # 这里暂时留空以便下次重试
                                continue 

                            # 组合
                            if trans_text:
                                item['translated'] = f"{prefix}{trans_text}{suffix}"
                            else:
                                # 只有标签
                                item['translated'] = f"{prefix}{core_texts[i]}{suffix}" # 翻译为空则用原文核心
                            
                            item['translated_at'] = datetime.now().isoformat()
                    
                    # 3. 更新进度 & 保存
                    completed_count += len(batch)
                    
                    # [优化] 使用 \r 打印进度，类似 tqdm
                    progress = completed_count / len(pending_items) * 100
                    print(f"\rJSON 翻译进度: {progress:.1f}% [{batch_idx+1}/{total_batches}]", end="", flush=True)
                    
                    self._save_progress(data, str(output_path))
                    
                except Exception as e:
                    logger.error(f"\n批次 {batch_idx+1} 处理失败: {e}")
                    # 继续下一个批次
            
            print() # 换行
            
            # 最终统计
            final_stats = self._get_translation_stats(data)
            final_stats['success'] = True
            final_stats['output_file'] = str(output_path)
            
            logger.info(f"JSON翻译完成! 最终覆盖率: {final_stats['progress']}%")
            return final_stats
            
        except Exception as e:
            logger.error(f"JSON处理失败: {e}")
            raise FileProcessingError(f"JSON处理失败: {e}")