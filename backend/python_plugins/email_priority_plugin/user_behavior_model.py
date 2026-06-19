# -*- coding: utf-8 -*-
"""
用户行为模型
基于用户历史操作（打开、回复、删除、忽略等）建模用户偏好
支持增量学习，持续优化优先级预测
"""

import json
import os
import logging
from typing import Any, Dict, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UserBehaviorModel:
    """
    用户行为统计模型
    追踪并分析用户与邮件的互动模式
    """

    def __init__(self):
        # 核心数据结构: {user_id: {sender_email: {统计信息}}}
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
            lambda: defaultdict(lambda: {
                'total_received': 0,
                'total_opened': 0,
                'total_replied': 0,
                'total_ignored': 0,
                'total_deleted': 0,
                'open_rate': 0.0,
                'reply_rate': 0.0,
                'interaction_count': 0,
                'last_interaction': None,  # ISO 格式时间戳
                'last_interaction_days': 999,
                'first_interaction': None,
                'avg_response_time_minutes': 0,
            })
        )

    def initialize_defaults(self) -> None:
        """
        使用合理的默认值初始化模型
        为假想的常见联系人预设基础数据
        """
        default_contacts = {
            'boss@company.com': {
                'open_rate': 0.95, 'reply_rate': 0.80,
                'interaction_count': 50,
            },
            'colleague@company.com': {
                'open_rate': 0.85, 'reply_rate': 0.60,
                'interaction_count': 30,
            },
            'hr@company.com': {
                'open_rate': 0.90, 'reply_rate': 0.40,
                'interaction_count': 15,
            },
            'newsletter@external.com': {
                'open_rate': 0.20, 'reply_rate': 0.01,
                'interaction_count': 100,
            },
            'noreply@service.com': {
                'open_rate': 0.50, 'reply_rate': 0.00,
                'interaction_count': 200,
            },
        }

        now = datetime.now()

        for sender, stats in default_contacts.items():
            entry = self._data['default'][sender]
            entry['total_received'] = stats['interaction_count']
            entry['total_opened'] = int(stats['interaction_count'] * stats['open_rate'])
            entry['total_replied'] = int(stats['interaction_count'] * stats['reply_rate'])
            entry['open_rate'] = stats['open_rate']
            entry['reply_rate'] = stats['reply_rate']
            entry['interaction_count'] = stats['interaction_count']
            entry['last_interaction'] = now.isoformat()
            entry['last_interaction_days'] = 1
            entry['first_interaction'] = (now - timedelta(days=90)).isoformat()

        logger.info("用户行为模型已初始化默认数据")

    def update(self, email_id: str, action: str, user_id: str = 'default',
                sender: str = '', timestamp: Optional[datetime] = None) -> None:
        """
        记录一次用户操作并更新统计
        Args:
            email_id: 邮件ID（用于引用，暂不存储详细记录）
            action: 'open' | 'reply' | 'delete' | 'ignore' | 'archive'
            user_id: 用户标识
            sender: 发件人地址
            timestamp: 操作时间，默认当前
        """
        if not sender:
            return

        ts = timestamp or datetime.now()

        entry = self._data[user_id][sender]
        entry['total_received'] += 1

        if action == 'open':
            entry['total_opened'] += 1
        elif action == 'reply':
            entry['total_opened'] += 1
            entry['total_replied'] += 1
        elif action == 'delete':
            entry['total_deleted'] += 1
        elif action in ('ignore', 'archive'):
            entry['total_ignored'] += 1

        entry['interaction_count'] += 1

        # 更新打开率
        total = entry['total_received']
        if total > 0:
            entry['open_rate'] = entry['total_opened'] / total
            entry['reply_rate'] = entry['total_replied'] / total

        # 更新最近互动时间
        if entry['last_interaction'] is None:
            entry['first_interaction'] = ts.isoformat()

        previous_ts = None
        if entry['last_interaction']:
            try:
                previous_ts = datetime.fromisoformat(entry['last_interaction'])
            except (ValueError, TypeError):
                pass

        entry['last_interaction'] = ts.isoformat()
        entry['last_interaction_days'] = 0

        # 估算平均响应时间
        if previous_ts and action in ('open', 'reply'):
            delta_minutes = (ts - previous_ts).total_seconds() / 60.0
            if entry['avg_response_time_minutes'] == 0:
                entry['avg_response_time_minutes'] = delta_minutes
            else:
                # 指数移动平均
                entry['avg_response_time_minutes'] = (
                    entry['avg_response_time_minutes'] * 0.8 + delta_minutes * 0.2
                )

    def get_sender_stats(self, sender: str,
                           user_id: str = 'default') -> Optional[Dict[str, Any]]:
        """
        获取某个发件人的历史统计
        Args:
            sender: 发件人地址
            user_id: 用户标识
        Returns:
            dict | None: 统计信息
        """
        if user_id not in self._data:
            return None

        stats = self._data[user_id].get(sender)
        if stats is None:
            return None

        # 动态更新距上次交互的天数
        if stats.get('last_interaction'):
            try:
                last_ts = datetime.fromisoformat(stats['last_interaction'])
                days = (datetime.now() - last_ts).days
                stats['last_interaction_days'] = days
            except (ValueError, TypeError):
                stats['last_interaction_days'] = 999

        return dict(stats)

    def get_all_stats(self, user_id: str = 'default') -> Dict[str, Any]:
        """
        获取指定用户的所有统计
        """
        return {
            sender: dict(stats)
            for sender, stats in self._data.get(user_id, {}).items()
        }

    def save(self, filepath: str) -> None:
        """
        保存模型到 JSON 文件
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        logger.info(f"用户行为模型已保存到 {filepath}")

    def load(self, filepath: str) -> None:
        """
        从 JSON 文件加载模型
        """
        if not os.path.exists(filepath):
            logger.warning(f"模型文件不存在: {filepath}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        # 转回 defaultdict 结构
        self._data = defaultdict(
            lambda: defaultdict(lambda: {
                'total_received': 0, 'total_opened': 0,
                'total_replied': 0, 'total_ignored': 0,
                'total_deleted': 0, 'open_rate': 0.0,
                'reply_rate': 0.0, 'interaction_count': 0,
                'last_interaction': None, 'last_interaction_days': 999,
                'first_interaction': None,
                'avg_response_time_minutes': 0,
            })
        )

        for user_id, senders in loaded.items():
            for sender, stats in senders.items():
                self._data[user_id][sender].update(stats)

        logger.info(f"用户行为模型已从 {filepath} 加载")

    def get_top_contacts(self, user_id: str = 'default',
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取高频联系TOP N
        """
        if user_id not in self._data:
            return []

        contacts = []
        for sender, stats in self._data[user_id].items():
            contacts.append({
                'sender': sender,
                'interaction_count': stats.get('interaction_count', 0),
                'reply_rate': stats.get('reply_rate', 0),
                'last_interaction_days': stats.get('last_interaction_days', 999),
            })

        contacts.sort(key=lambda x: x['interaction_count'], reverse=True)
        return contacts[:limit]