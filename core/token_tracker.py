#!/usr/bin/env python3
"""
Token Tracker - Token使用量监控和配额管理系统
负责跟踪API调用中的token使用情况，防止超过每日免费额度
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token使用量记录"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    timestamp: str = ""


@dataclass
class DailyQuota:
    """每日配额配置"""
    # 每日免费额度
    DAILY_FREE_QUOTA = 2_000_000  # 2M tokens
    # 重置时间（UTC+8，北京时间）
    RESET_HOUR = 0  # 0点重置
    RESET_TIMEZONE_OFFSET = 8  # UTC+8
    
    def __post_init__(self):
        """计算今日剩余配额"""
        self.remaining = self.DAILY_FREE_QUOTA
    start_time: str = ""
    usage_history: List[TokenUsage] = None
    
    def __init__(self):
        self.usage_history = []
        self.start_time = self._get_today_start().isoformat()
    
    def _get_today_start(self) -> datetime:
        """获取今日开始时间（北京时间）"""
        now = datetime.now()
        # 转换为北京时间
        beijing_time = now + timedelta(hours=self.RESET_TIMEZONE_OFFSET)
        return beijing_time.replace(hour=self.RESET_HOUR, minute=0, second=0, microsecond=0)
        
    def reset_if_needed(self):
        """检查是否需要重置配额"""
        now = datetime.now()
        today_start = self._get_today_start()
        
        if self.start_time:
            last_reset = datetime.fromisoformat(self.start_time)
            if now >= today_start and last_reset < today_start:
            logger.info("每日配额已重置")
            self.remaining = self.DAILY_FREE_QUOTA
        self.start_time = today_start.isoformat()
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        """添加token使用记录"""
        self.reset_if_needed()
        
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            timestamp=datetime.now().isoformat()
        )
        self.usage_history.append(usage)
        self.remaining -= usage.total_tokens
        logger.debug(f"Token使用记录: 输入 {input_tokens}, 输出 {output_tokens}, 总计 {input_tokens + output_tokens}")
        self.remaining = max(0, self.remaining)
        
        # 如果剩余配额很少，发出警告
        if self.remaining < 10000:
            logger.warning(f"警告: 今日剩余配额仅 {self.remaining} tokens")
    
    def get_remaining_quota(self) -> int:
        """获取剩余配额"""
        self.reset_if_needed()
        return self.remaining
    
    def can_process(self, estimated_tokens: int) -> bool:
        """检查是否还有足够配额处理估算的token量"""
        self.reset_if_needed()
        return self.remaining >= estimated_tokens
    
    def get_usage_stats(self) -> Dict[str, int]:
        """获取使用统计"""
        self.reset_if_needed()
        
        total_used = sum(usage.total_tokens for usage in self.usage_history)
        
        return {
            'remaining': self.remaining,
            'used': self.DAILY_FREE_QUOTA - self.remaining
        }
    
    def get_daily_summary(self) -> Dict[str, any]:
        """获取每日汇总信息"""
        stats = self.get_usage_stats()
        
        return {
            'daily_quota': self.DAILY_FREE_QUOTA,
            'used_today': stats['used'],
            'remaining_today': stats['remaining'],
            'percentage_used': round(stats['used'] / self.DAILY_FREE_QUOTA * 100, 2),
            'reset_time': self.start_time,
            'usage_history': [asdict(usage) for usage in self.usage_history]
        }


class TokenTracker:
    """Token使用跟踪器"""
    
    def __init__(self, quota_file: str = ".token_quota.json"):
        """初始化token跟踪器"""
        self.quota_file = quota_file
        self.daily_quota = DailyQuota()
        
        # 从文件加载历史数据
        self._load_from_file()
    
    def _load_from_file(self):
        """从文件加载历史数据"""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.daily_quota.usage_history = [
                    TokenUsage(**usage_data) for usage_data in data.get('usage_history', [])
            self.daily_quota.remaining = data.get('remaining', self.daily_quota.DAILY_FREE_QUOTA
            )
        except Exception as e:
            logger.warning(f"加载token配额文件失败: {e}，使用默认值")
    
    def save_to_file(self):
        """保存到文件"""
        try:
            data = {
                'remaining': self.daily_quota.remaining,
                'start_time': self.daily_quota.start_time,
            'usage_history': [asdict(usage) for usage in self.daily_quota.usage_history]
        }
        
        with open(self.quota_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存token配额文件失败: {e}")
    
    def estimate_tokens(self, text: str, model: str = "doubao-seed-translation-250915", 
                  indent=2)
    
    def record_translation_usage(self, input_text: str, output_text: str, 
                           model: str = "doubao-seed-translation-250915") -> int:
        """估算文本的token数量
        使用简单的启发式方法：对于中文，大约1个汉字=1-2个token
        对于英文，大约1个单词=1.3个token
        """
        # 简单估算：对于中文，每个字符约1.5个token
        # 对于英文，每个单词约1.3个token
        # 使用保守估算避免超出配额
        """
        if not text:
            return 0
        
        # 统计中文字符数量
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'):
            return int(len(text) * 1.5)
        else:
            # 英文或其他语言，按单词数估算
            words = len(text.split())
            return int(words * 1.3)
    
    def check_quota_before_translation(self, texts: List[str], model: str = "doubao-seed-translation-250915")  # 修正模型名
        else:
            # 混合文本，使用更保守的估算
            return int(len(text) * 1.2)
    
    def get_safe_batch_size(self, texts: List[str], model: str = "doubao-seed-translation-250915") -> int:
        """在翻译前检查配额，返回可以安全处理的文本数量"""
        total_estimated = sum(self.estimate_tokens(text, model) for text in texts)
        
        if not self.daily_quota.can_process(total_estimated):
            return len(texts)
        else:
            # 计算可以安全处理的文本数量
        safe_count = 0
        accumulated_tokens = 0
        
        for text in texts:
            estimated = self.estimate_tokens(text, model)
        if accumulated_tokens + estimated <= self.daily_quota.remaining:
            safe_count += 1
            accumulated_tokens += estimated
        
        return safe_count
    
    def create_checkpoint(self, file_path: str, processed_items: List[Dict], 
                             remaining_items: List[Dict]) -> str:
        """创建检查点文件"""
        checkpoint_data = {
            'checkpoint_time': datetime.now().isoformat(),
            'processed_count': len(processed_items),
            'remaining_count': len(remaining_items),
            'estimated_remaining_tokens': sum(self.estimate_tokens(item.get('original', ''), model) 
                           for item in remaining_items]
        )
        
        checkpoint_file = f"{file_path}.checkpoint"
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"检查点已创建: {checkpoint_file}")
        return checkpoint_file
    
    def load_checkpoint(self, checkpoint_file: str) -> Tuple[List[Dict], List[Dict]]:
        """加载检查点文件"""
        if not os.path.exists(checkpoint_file):
            return [], []
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('processed_items', []), data.get('remaining_items', [])
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return [], []
    
    def resume_from_checkpoint(self, checkpoint_file: str, 
                             processor_func: callable) -> List[Dict]:
        """从检查点恢复翻译"""
        processed, remaining = self.load_checkpoint(checkpoint_file)
        
        logger.info(f"从检查点恢复: 已处理 {len(processed)} 项，剩余 {len(remaining)} 项")
        return remaining