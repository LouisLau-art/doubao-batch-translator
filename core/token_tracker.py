#!/usr/bin/env python3
"""
Token Tracker - Token使用量监控和配额管理系统
负责跟踪API调用中的token使用情况，防止超过每日免费额度
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field

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
    RESET_HOUR = 0
    RESET_TIMEZONE_OFFSET = 8
    
    start_time: str = ""
    remaining: int = DAILY_FREE_QUOTA
    usage_history: List[TokenUsage] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.start_time:
            self.start_time = self._get_today_start().isoformat()
            
    def _get_today_start(self) -> datetime:
        """获取今日开始时间（北京时间）"""
        now = datetime.utcnow() + timedelta(hours=self.RESET_TIMEZONE_OFFSET)
        return now.replace(hour=self.RESET_HOUR, minute=0, second=0, microsecond=0)
        
    def reset_if_needed(self):
        """检查是否需要重置配额"""
        now = datetime.utcnow() + timedelta(hours=self.RESET_TIMEZONE_OFFSET)
        today_start = self._get_today_start()
        
        last_reset = datetime.fromisoformat(self.start_time) if self.start_time else datetime.min
        
        # 如果当前时间超过了今天的重置点，且上次重置时间早于今天的重置点
        if now >= today_start and last_reset < today_start:
            logger.info("每日配额已重置")
            self.remaining = self.DAILY_FREE_QUOTA
            self.usage_history = []
            self.start_time = today_start.isoformat()
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        """添加token使用记录"""
        self.reset_if_needed()
        
        total = input_tokens + output_tokens
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            timestamp=datetime.now().isoformat()
        )
        self.usage_history.append(usage)
        self.remaining = max(0, self.remaining - total)
        
        logger.debug(f"Token使用: +{total} (剩余: {self.remaining})")
        
        if self.remaining < 50000:
            logger.warning(f"警告: 今日剩余配额仅 {self.remaining} tokens")
    
    def can_process(self, estimated_tokens: int) -> bool:
        """检查是否还有足够配额"""
        self.reset_if_needed()
        return self.remaining >= estimated_tokens


class TokenTracker:
    """Token使用跟踪器 (单例模式建议在应用层控制)"""
    
    def __init__(self, quota_file: str = ".token_quota.json"):
        self.quota_file = quota_file
        self.daily_quota = DailyQuota()
        self._load_from_file()
    
    def _load_from_file(self):
        """从文件加载历史数据"""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.daily_quota.start_time = data.get('start_time', "")
                self.daily_quota.remaining = data.get('remaining', DailyQuota.DAILY_FREE_QUOTA)
                
                history = data.get('usage_history', [])
                self.daily_quota.usage_history = [TokenUsage(**u) for u in history]
                
                # 加载后立即检查是否需要重置
                self.daily_quota.reset_if_needed()
                
            except Exception as e:
                logger.warning(f"加载token配额文件失败: {e}，使用默认值")
    
    def save_to_file(self):
        """保存到文件"""
        try:
            data = {
                'remaining': self.daily_quota.remaining,
                'start_time': self.daily_quota.start_time,
                'usage_history': [asdict(u) for u in self.daily_quota.usage_history]
            }
            with open(self.quota_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存token配额文件失败: {e}")
            
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量
        中文: ~1.5 token/char
        英文: ~1.3 token/word
        """
        if not text: return 0
        
        # 简单判定：如果包含大量非ASCII字符，视为中文/多字节语言
        non_ascii_count = len([c for c in text if ord(c) > 127])
        
        if non_ascii_count / len(text) > 0.1:
            # 中文模式
            return int(len(text) * 1.5)
        else:
            # 英文模式 (按空格分词)
            return int(len(text.split()) * 1.3)

    def record_usage(self, input_text: str, output_text: str):
        """记录一次翻译的使用量"""
        in_tokens = self.estimate_tokens(input_text)
        out_tokens = self.estimate_tokens(output_text)
        self.daily_quota.add_usage(in_tokens, out_tokens)
        self.save_to_file()

    def check_batch_limit(self, texts: List[str]) -> int:
        """
        检查一批文本中有多少可以安全处理
        Returns: safe_count (前N个可以处理)
        """
        self.daily_quota.reset_if_needed()
        remaining = self.daily_quota.remaining
        
        accumulated = 0
        safe_count = 0
        
        for text in texts:
            cost = self.estimate_tokens(text) * 2  # *2 是预估输出也消耗这么多
            if accumulated + cost <= remaining:
                accumulated += cost
                safe_count += 1
            else:
                break
                
        return safe_count