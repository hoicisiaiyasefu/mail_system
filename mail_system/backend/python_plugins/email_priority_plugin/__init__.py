# -*- coding: utf-8 -*-
"""
邮件优先级排序插件 (Email Priority Plugin)
基于用户历史行为预测邮件重要性，自动排序收件箱
"""

from .priority_engine import PriorityEngine, create_priority_engine

__all__ = [
    "PriorityEngine",
    "create_priority_engine",
]