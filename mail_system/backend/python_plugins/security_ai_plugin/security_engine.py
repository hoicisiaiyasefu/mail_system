# -*- coding: utf-8 -*-
"""
安全与多媒体处理 AI 引擎
检测复杂安全威胁：伪造发件人、隐藏恶意链接、钓鱼邮件等
支持实时处理 + 异步深度分析
"""

import os
import re
import json
import sys
import logging
from typing import Any, Dict, List, Optional

from plugin_interface import EmailPluginBase
from .threat_detector import ThreatDetector
from .link_analyzer import LinkAnalyzer
from .spoof_detector import SpoofDetector
from .llm_api import LLMServiceProvider

# 尝试导入公共 LLM provider（PluginRegistry 会通过 _llm_provider 注入）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
try:
    from llm_sdk_provider import BaseLLMProvider  # noqa: F401
except ImportError:
    BaseLLMProvider = None  # type: ignore

logger = logging.getLogger(__name__)


class SecurityEngine(EmailPluginBase):
    """
    AI 安全检测引擎
    实现 EmailPluginBase 接口，可插拔集成

    检测维度：
    - 伪造发件人（SPF/DKIM 模拟 + 内容分析）
    - 隐藏恶意链接（URL 重定向、短链接展开、域名仿冒）
    - 钓鱼邮件识别（关键词 + 模式匹配 + LLM 语义）
    - 恶意附件检测（文件类型伪装、宏病毒识别）
    - 社会工程学攻击检测
    """

    name = "security_ai_engine"
    version = "1.0.0"
    is_async = False  # 安全检测需要实时处理（邮件一到就分析）

    # 风险等级
    RISK_SAFE = 'safe'          # 安全
    RISK_LOW = 'low'            # 低风险
    RISK_MEDIUM = 'medium'      # 中风险
    RISK_HIGH = 'high'          # 高风险
    RISK_CRITICAL = 'critical'  # 严重威胁

    def __init__(self):
        super().__init__()
        self.threat_detector: Optional[ThreatDetector] = None
        self.link_analyzer: Optional[LinkAnalyzer] = None
        self.spoof_detector: Optional[SpoofDetector] = None
        self.llm_service: Optional[LLMServiceProvider] = None
        self.llm_enabled: bool = False
        self._initialized: bool = False

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化安全引擎
        Args:
            config: {
                'llm_api_key': str,         # 大模型 API Key（可选，用于深度分析）
                'llm_provider': str,        # 'openai' / 'custom'
                'llm_model': str,           # 模型名称
                'llm_base_url': str,        # 自定义 API URL
                'whitelist_file': str,      # 白名单文件路径
                'blacklist_file': str,      # 黑名单文件路径
                'enable_link_expand': bool, # 是否展开短链接
            }
        """
        try:
            config = config or {}

            # 初始化子模块
            self.threat_detector = ThreatDetector()
            self.link_analyzer = LinkAnalyzer(
                expand_short_urls=config.get('enable_link_expand', True)
            )
            self.spoof_detector = SpoofDetector(
                whitelist_file=config.get('whitelist_file'),
                blacklist_file=config.get('blacklist_file'),
            )

            # 可选 LLM — 优先使用 PluginRegistry 注入的共享 provider
            shared_llm = config.get('_llm_provider')
            if shared_llm is not None and BaseLLMProvider is not None and isinstance(shared_llm, BaseLLMProvider):
                # 创建轻量 Shell，底层复用共享连接
                self.llm_service = LLMServiceProvider(_shared_provider=shared_llm)
                self.llm_enabled = shared_llm.test_connection()
            else:
                llm_api_key = config.get('llm_api_key')
                if llm_api_key:
                    self.llm_service = LLMServiceProvider(
                        api_key=llm_api_key,
                        provider=config.get('llm_provider', 'openai'),
                        model=config.get('llm_model', 'gpt-3.5-turbo'),
                        base_url=config.get('llm_base_url'),
                    )
                    self.llm_enabled = self.llm_service.test_connection()

            self._initialized = True
            logger.info(f"安全引擎初始化完成, LLM: {'已启用' if self.llm_enabled else '未启用'}")
            return True

        except Exception as e:
            logger.error(f"安全引擎初始化失败: {e}")
            return False

    def process(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        实时分析邮件安全威胁
        Args:
            email_data: 邮件数据
        Returns:
            dict: {
                'plugin_name': str,
                'risk_level': str,           # 'safe'/'low'/'medium'/'high'/'critical'
                'risk_score': float,         # 0.0~1.0
                'threats': list,             # 检测到的威胁列表
                'is_spoofed': bool,          # 是否伪造发件人
                'malicious_links': list,     # 恶意链接列表
                'suspicious_attachments': list,
                'recommendation': str,       # 处理建议
            }
        """
        from_email = email_data.get('from', '')
        subject = email_data.get('subject', '')
        content = email_data.get('content', '')
        headers = email_data.get('headers', {})
        attachments = email_data.get('attachments', [])

        threats = []
        risk_score = 0.0

        # 1. 伪造发件人检测
        spoof_result = self.spoof_detector.detect(from_email, content, headers)
        if spoof_result['is_spoofed']:
            threats.append({
                'type': 'spoofed_sender',
                'severity': 'high',
                'detail': spoof_result['reason'],
                'confidence': spoof_result['confidence'],
            })
            risk_score += 0.40

        # 2. 链接分析
        link_result = self.link_analyzer.analyze(content)
        malicious_links = link_result.get('malicious', [])
        suspicious_links = link_result.get('suspicious', [])

        for link in malicious_links:
            threats.append({
                'type': 'malicious_link',
                'severity': 'critical',
                'detail': f"恶意链接: {link['url']}",
                'url': link['url'],
                'reason': link.get('reason', ''),
            })
            risk_score += 0.35

        for link in suspicious_links:
            threats.append({
                'type': 'suspicious_link',
                'severity': 'medium',
                'detail': f"可疑链接: {link['url']}",
                'url': link['url'],
                'reason': link.get('reason', ''),
            })
            risk_score += 0.15

        # 3. 钓鱼邮件检测
        phishing_result = self.threat_detector.detect_phishing(subject, content, from_email)
        if phishing_result['is_phishing']:
            threats.append({
                'type': 'phishing',
                'severity': 'high',
                'detail': phishing_result['reason'],
                'confidence': phishing_result['confidence'],
            })
            risk_score += 0.40

        # 4. 附件安全检测
        suspicious_attachment_names = []
        if attachments:
            attachment_result = self.threat_detector.analyze_attachments(attachments)
            suspicious_attachments = attachment_result.get('suspicious', [])
            for att in suspicious_attachments:
                threats.append({
                    'type': 'suspicious_attachment',
                    'severity': 'high' if att.get('dangerous') else 'medium',
                    'detail': f"可疑附件: {att.get('filename', 'unknown')}",
                    'filename': att.get('filename', ''),
                    'reason': att.get('reason', ''),
                })
                risk_score += 0.30 if att.get('dangerous') else 0.10
            suspicious_attachment_names = [
                a.get('filename') for a in suspicious_attachments
            ]

        # 5. 大模型深度分析（可选）
        if self.llm_enabled and self.llm_service:
            llm_result = self.llm_service.detect_malicious_intent(
                content,
                links=[l['url'] for l in malicious_links + suspicious_links]
            )
            if llm_result.get('malicious'):
                threats.append({
                    'type': 'llm_analysis',
                    'severity': 'high',
                    'detail': llm_result.get('reason', '大模型检测到可疑内容'),
                    'risk_type': llm_result.get('risk_type', '未知'),
                })
                # LLM 与规则引擎融合：如果规则已检测到威胁，LLM 确认视为高风险
                if risk_score > 0:
                    # 规则已发现威胁，LLM 确认 → 乘法放大融合
                    risk_score = risk_score + (1.0 - risk_score) * 0.5
                else:
                    risk_score += 0.20

        # 归一化风险分数
        risk_score = min(risk_score, 1.0)

        # 确定风险等级（降低阈值以提升敏感度）
        risk_level = self._get_risk_level(risk_score)

        # 生成处理建议
        recommendation = self._generate_recommendation(risk_level, threats)

        return {
            'plugin_name': self.name,
            'risk_level': risk_level,
            'risk_score': round(risk_score, 4),
            'threats': threats,
            'is_spoofed': spoof_result.get('is_spoofed', False),
            'malicious_links': malicious_links,
            'suspicious_attachments': suspicious_attachment_names,
            'recommendation': recommendation,
        }

    def _get_risk_level(self, score: float) -> str:
        """分数转风险等级（降低阈值以提升检测敏感度）"""
        if score >= 0.65:
            return self.RISK_CRITICAL
        elif score >= 0.45:
            return self.RISK_HIGH
        elif score >= 0.20:
            return self.RISK_MEDIUM
        elif score >= 0.05:
            return self.RISK_LOW
        else:
            return self.RISK_SAFE

    def _generate_recommendation(self, level: str,
                                   threats: List[Dict]) -> str:
        """生成处理建议"""
        recommendations = {
            'safe': '邮件安全，可正常处理',
            'low': '建议标记为可疑，用户自行判断',
            'medium': '建议隔离处理，通知用户注意',
            'high': '建议移至垃圾邮件，警告用户',
            'critical': '建议立即隔离，阻止访问链接，通知安全团队',
        }

        base = recommendations.get(level, '未知风险')
        threat_types = set(t['type'] for t in threats)
        if 'malicious_link' in threat_types:
            base += '；检测到恶意链接'
        if 'spoofed_sender' in threat_types:
            base += '；发件人疑似伪造'
        if 'phishing' in threat_types:
            base += '；疑似钓鱼邮件'

        return base

    def shutdown(self) -> None:
        """关闭引擎"""
        if self.llm_service:
            self.llm_service.close()
        self._initialized = False
        logger.info("安全引擎已关闭")


def create_security_engine(config: Optional[Dict[str, Any]] = None) -> SecurityEngine:
    """工厂函数"""
    engine = SecurityEngine()
    engine.init(config)
    return engine