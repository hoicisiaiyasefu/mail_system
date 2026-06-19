# -*- coding: utf-8 -*-
"""
安全与多媒体处理 AI 插件 (Security AI Plugin)
检测伪造发件人、隐藏恶意链接等复杂安全威胁
"""

from .security_engine import SecurityEngine, create_security_engine

__all__ = [
    "SecurityEngine",
    "create_security_engine",
]