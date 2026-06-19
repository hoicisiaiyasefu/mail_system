# -*- coding: utf-8 -*-
"""
伪造发件人检测模块
模拟 SPF/DKIM 验证 + 邮件头分析 + 内容一致性检测
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SpoofDetector:
    """伪造发件人检测器"""

    # 常见品牌/机构的官方域名（用于一致性检查）
    BRAND_SENDER_PATTERNS = {
        'paypal.com': r'^[a-z0-9._%+-]+@paypal\.com$',
        'apple.com': r'^[a-z0-9._%+-]+@(?:apple\.com|icloud\.com)$',
        'microsoft.com': r'^[a-z0-9._%+-]+@(?:microsoft\.com|office365\.com|outlook\.com)$',
        'amazon.com': r'^[a-z0-9._%+-]+@(?:amazon\.com|amazon\.\w+)$',
        'facebook.com': r'^[a-z0-9._%+-]+@(?:facebookmail\.com|facebook\.com|fb\.com)$',
        'alibaba.com': r'^[a-z0-9._%+-]+@(?:alibaba-inc\.com|alibaba\.com)$',
        'taobao.com': r'^[a-z0-9._%+-]+@(?:taobao\.com|alibaba-inc\.com)$',
    }

    # 常见伪造发件人的显示名欺诈模式
    SPOOF_DISPLAY_PATTERNS = [
        re.compile(r'^.*<([^>]+)>$'),  # Display Name <email>
    ]

    def __init__(self, whitelist_file: Optional[str] = None,
                  blacklist_file: Optional[str] = None):
        self.whitelist = self._load_list(whitelist_file)
        self.blacklist = self._load_list(blacklist_file)

    def _load_list(self, filepath: Optional[str]) -> set:
        """加载白名单/黑名单"""
        items = set()
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            items.add(line.lower())
            except Exception as e:
                logger.warning(f"加载名单失败: {filepath}, {e}")
        return items

    def detect(self, from_email: str, content: str,
                headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测伪造发件人
        Args:
            from_email: From 地址（可能包含显示名）
            content: 邮件正文
            headers: 邮件头部信息
        Returns:
            {'is_spoofed': bool, 'confidence': float, 'reason': str}
        """
        reasons = []
        confidence = 0.0

        # 解析发件人地址
        actual_email, display_name = self._parse_from(from_email)

        # 1. 黑名单/白名单检查
        if actual_email and actual_email.lower() in self.blacklist:
            return {
                'is_spoofed': True,
                'confidence': 1.0,
                'reason': '发件人在黑名单中',
            }

        if actual_email and actual_email.lower() in self.whitelist:
            return {
                'is_spoofed': False,
                'confidence': 0.0,
                'reason': '发件人在白名单中',
            }

        # 2. 邮件头分析（模拟 SPF/DKIM 结果）
        header_result = self._analyze_headers(headers, actual_email)
        if header_result['suspicious']:
            reasons.append(header_result['reason'])
            confidence += 0.35

        # 3. 显示名欺诈检测
        if display_name and actual_email:
            display_result = self._check_display_name_spoof(
                display_name, actual_email
            )
            if display_result['suspicious']:
                reasons.append(display_result['reason'])
                confidence += 0.30

        # 4. 发件人域名与内容一致性
        if actual_email:
            consistency_result = self._check_content_consistency(
                actual_email, content
            )
            if consistency_result['suspicious']:
                reasons.append(consistency_result['reason'])
                confidence += 0.25

        # 5. Reply-To 与 From 不一致
        reply_to = headers.get('Reply-To', '')
        if reply_to and actual_email:
            reply_email = self._extract_email(reply_to)
            if reply_email and actual_email.lower() != reply_email.lower():
                from_domain = actual_email.split('@')[1].lower() if '@' in actual_email else ''
                reply_domain = reply_email.split('@')[1].lower() if '@' in reply_email else ''
                if from_domain != reply_domain:
                    reasons.append(
                        f"Reply-To({reply_email})与From({actual_email})域名不一致"
                    )
                    confidence += 0.20

        # 6. Return-Path 与 From 不一致
        return_path = headers.get('Return-Path', '')
        if return_path and actual_email:
            return_email = self._extract_email(return_path)
            if return_email and actual_email.lower() != return_email.lower():
                reasons.append(
                    f"Return-Path({return_email})与From({actual_email})不一致"
                )
                confidence += 0.15

        is_spoofed = confidence >= 0.5
        reason = '; '.join(reasons) if reasons else '未检测到伪造迹象'

        return {
            'is_spoofed': is_spoofed,
            'confidence': min(confidence, 1.0),
            'reason': reason,
        }

    def _parse_from(self, from_field: str) -> Tuple[str, str]:
        """
        解析 From 字段
        Returns:
            (email_addr, display_name)
        """
        if not from_field:
            return '', ''

        # 格式: Display Name <email@domain.com>
        match = re.match(r'^([^<]*)\s*<([^>]+)>\s*$', from_field)
        if match:
            display_name = match.group(1).strip().strip('"')
            email_addr = match.group(2).strip()
            return email_addr, display_name

        # 可能只是纯邮件地址
        if '@' in from_field:
            return from_field.strip(), ''

        return '', from_field.strip()

    def _extract_email(self, field: str) -> str:
        """从字段中提取邮件地址"""
        if not field:
            return ''
        match = re.search(r'<([^>]+)>', field)
        if match:
            return match.group(1).strip()
        if '@' in field:
            return field.strip()
        return ''

    def _analyze_headers(self, headers: Dict[str, Any],
                          from_email: str) -> Dict[str, Any]:
        """
        分析邮件头部，模拟 SPF/DKIM 验证
        在实际系统中，这部分需要解析 Authentication-Results 头
        """
        if not headers:
            return {'suspicious': False, 'reason': ''}

        auth_results = headers.get('Authentication-Results', '')

        # SPF 失败
        if auth_results and 'spf=fail' in auth_results.lower():
            return {'suspicious': True, 'reason': 'SPF验证失败'}

        # DKIM 失败
        if auth_results and 'dkim=fail' in auth_results.lower():
            return {'suspicious': True, 'reason': 'DKIM签名验证失败'}

        # DMARC 失败
        if auth_results and 'dmarc=fail' in auth_results.lower():
            return {'suspicious': True, 'reason': 'DMARC验证失败'}

        # 缺少 Authentication-Results
        if not auth_results:
            # 检查 Received 链是否有异常
            received_headers = headers.get('Received', [])
            if isinstance(received_headers, str):
                received_headers = [received_headers]

            if not received_headers:
                return {'suspicious': True, 'reason': '缺少Received邮件头，可能伪造'}

            # 检查第一条 Received 中的域名
            first_received = received_headers[0] if received_headers else ''
            if from_email and '@' in from_email:
                sender_domain = from_email.split('@')[1].lower()
                if sender_domain not in first_received.lower():
                    return {
                        'suspicious': True,
                        'reason': '发送域名与Received头部不匹配'
                    }

        return {'suspicious': False, 'reason': ''}

    def _check_display_name_spoof(self, display_name: str,
                                     actual_email: str) -> Dict[str, Any]:
        """
        检测显示名欺诈
        例如：显示名为 "PayPal Support" 但实际邮箱是 xxx@gmail.com
        """
        display_lower = display_name.lower()

        # 检查显示名是否伪装成知名品牌
        brand_keywords = {
            'paypal': r'paypal\.com',
            'apple': r'(?:apple\.com|icloud\.com)',
            'microsoft': r'(?:microsoft\.com|office365\.com|outlook\.com)',
            'amazon': r'amazon\.\w+',
            'google': r'google\.com',
            'facebook': r'(?:facebook\.com|facebookmail\.com)',
            'bank of america': r'(?:bofa\.com|bankofamerica\.com)',
            'alibaba': r'alibaba',
            'taobao': r'taobao',
            'wechat': r'wechat',
            '支付宝': r'(?:alipay|alibaba)',
        }

        for brand, expected_domain in brand_keywords.items():
            if brand in display_lower:
                # 显示名声称是某品牌，检查实际邮箱域名
                if '@' in actual_email:
                    domain = actual_email.split('@')[1].lower()
                    if not re.search(expected_domain, domain):
                        return {
                            'suspicious': True,
                            'reason': (
                                f'显示名声称"{brand}"，但实际邮箱域名为{domain}，'
                                f'疑似伪造'
                            )
                        }

        return {'suspicious': False, 'reason': ''}

    def _check_content_consistency(self, from_email: str,
                                      content: str) -> Dict[str, Any]:
        """检测发件人身份与邮件内容的一致性"""
        if '@' not in from_email:
            return {'suspicious': False, 'reason': ''}

        domain = from_email.split('@')[1].lower()
        content_lower = content.lower()

        # 检查品牌域名与内容的一致性
        brand_expected_keywords = {
            'paypal.com': ['paypal', 'transaction', 'payment'],
            'apple.com': ['apple', 'iphone', 'ipad', 'mac', 'icloud'],
            'microsoft.com': ['microsoft', 'windows', 'office', 'outlook', 'teams'],
            'amazon.com': ['amazon', 'order', 'shipping', 'prime'],
            'facebook.com': ['facebook', 'notification', 'friend'],
            'alibaba.com': ['alibaba', 'trade', 'supplier'],
        }

        for brand_domain, keywords in brand_expected_keywords.items():
            if domain == brand_domain or domain.endswith(f'.{brand_domain}'):
                # 是官方域名，检查内容是否包含该品牌相关内容
                found = any(kw in content_lower for kw in keywords)
                if not found and len(content) > 100:
                    return {
                        'suspicious': True,
                        'reason': (
                            f'发件人域名为{brand_domain}，但内容非{brand_domain}相关，'
                            f'可能被盗用'
                        )
                    }

        return {'suspicious': False, 'reason': ''}