# -*- coding: utf-8 -*-
"""
基于机器学习的垃圾邮件识别插件
Spam ML Plugin - 使用 TF-IDF + 朴素贝叶斯/SVM 进行垃圾邮件检测
通过 DLL 动态链接库方式加载（支持 ctypes 加载 ONNX 推理引擎）
"""

from plugin_interface import EmailPluginBase
from .ml_spam_detector import MLSpamDetector

__version__ = "1.0.0"
__all__ = ["EmailPluginBase", "MLSpamDetector"]