# -*- coding: utf-8 -*-
"""
威胁检测模块
检测钓鱼邮件、恶意附件、社会工程学攻击等
"""

import re
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ThreatDetector:
    """威胁检测器"""

    # 钓鱼邮件关键词特征
    PHISHING_KEYWORDS = {
        'banking': [
            '银行', '账户', '密码', '验证', '登录', '异常',
            'bank', 'account', 'password', 'verify', 'login',
            'suspended', 'unusual activity', 'confirm',
        ],
        'prize_scam': [
            '中奖', '获奖', '奖金', '奖品', '领奖',
            'winner', 'prize', 'lottery', 'congratulations',
        ],
        'urgent_action': [
            '立即', '尽快', '紧急', '失效', '过期', '锁定',
            'urgent', 'immediately', 'action required', 'expired',
            'verify now', 'click here', 'limited time',
        ],
        'payment': [
            '付款', '转账', '汇款', '退款', '欠款',
            'payment', 'transfer', 'refund', 'invoice',
        ],
        'tech_support': [
            '技术支持', '维修', '病毒', '感染', '扫描',
            'tech support', 'virus', 'infected', 'scan',
        ],
    }

    # 高危附件扩展名
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh',
        '.ps1', '.psm1', '.psd1', '.hta', '.msi',
        '.jar', '.dll', '.sys', '.reg',
    ]

    # 可疑附件扩展名（可能伪装）
    SUSPICIOUS_EXTENSIONS = [
        '.zip', '.rar', '.7z', '.iso', '.img',
        '.docm', '.xlsm', '.pptm',  # 带宏的 Office 文件
        '.pdf', '.html', '.htm',
    ]

    # 双重扩展名伪装模式
    DOUBLE_EXTENSION_PATTERN = re.compile(
        r'\.(doc|xls|ppt|pdf|txt|jpg|png|mp3|mp4|zip|rar)\.'
        r'(exe|bat|cmd|vbs|js|com|scr|pif|hta|msi)$',
        re.IGNORECASE
    )

    def detect_phishing(self, subject: str, content: str,
                         from_email: str) -> Dict[str, Any]:
        """
        检测钓鱼邮件
        Returns:
            {
                'is_phishing': bool,
                'confidence': float,
                'reason': str,
                'matched_categories': list,
            }
        """
        text = f"{subject} {content[:3000]}"
        text_lower = text.lower()

        matched_categories = []
        total_matches = 0
        category_scores = {}

        for category, keywords in self.PHISHING_KEYWORDS.items():
            matches = 0
            for kw in keywords:
                if kw.lower() in text_lower:
                    matches += text_lower.count(kw.lower())
            if matches > 0:
                matched_categories.append(category)
                # 不同类别权重不同
                weight = {
                    'banking': 0.9,
                    'urgent_action': 0.85,
                    'payment': 0.8,
                    'prize_scam': 0.75,
                    'tech_support': 0.7,
                }.get(category, 0.5)

                category_scores[category] = min(matches / len(keywords), 1.0) * weight
                total_matches += matches

        # 链接检测
        url_pattern = re.compile(r'https?://[^\s<>"]+')
        urls = url_pattern.findall(text)

        suspicious_url_count = 0
        for url in urls:
            if self._is_suspicious_url(url):
                suspicious_url_count += 1

        # IP 地址形式的 URL
        ip_url_pattern = re.compile(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        ip_urls = ip_url_pattern.findall(text)
        suspicious_url_count += len(ip_urls) * 2

        # 综合评分
        confidence = 0.0
        if matched_categories:
            category_score = sum(category_scores.values()) / len(matched_categories)
            confidence += category_score * 0.4

        if suspicious_url_count > 0:
            confidence += min(suspicious_url_count / 5.0, 1.0) * 0.3

        # 发件人域名可疑度
        if from_email and self._is_suspicious_domain(from_email):
            confidence += 0.3

        # 主题中包含误导性文字（如 Re: Fwd: 等伪装）
        misleading_patterns = [
            r'^re:\s*(re:|fwd:)*',      # 多层回复伪装
            r'^(fw|fwd):\s*(fw|fwd:)*',  # 多层转发伪装
        ]
        for pattern in misleading_patterns:
            if re.match(pattern, subject, re.IGNORECASE):
                confidence += 0.1
                break

        is_phishing = confidence >= 0.4

        reason_parts = []
        if matched_categories:
            reason_parts.append(
                f"匹配钓鱼特征类别: {', '.join(matched_categories)}"
            )
        if suspicious_url_count > 0:
            reason_parts.append(f"检测到{suspicious_url_count}个可疑链接")

        reason = '; '.join(reason_parts) if reason_parts else '未检测到明确威胁'

        return {
            'is_phishing': is_phishing,
            'confidence': min(confidence, 1.0),
            'reason': reason,
            'matched_categories': matched_categories,
        }

    def analyze_attachments(self, attachments: List[Dict[str, Any]]
                             ) -> Dict[str, Any]:
        """
        分析附件安全性
        Args:
            attachments: [{'filename': str, 'size': int, ...}]
        Returns:
            {'suspicious': [{'filename': str, 'dangerous': bool, 'reason': str}]}
        """
        suspicious = []

        for att in attachments:
            filename = att.get('filename', '')
            size = att.get('size', 0)

            if not filename:
                continue

            filename_lower = filename.lower()

            # 1. 检查危险扩展名
            for ext in self.DANGEROUS_EXTENSIONS:
                if filename_lower.endswith(ext):
                    suspicious.append({
                        'filename': filename,
                        'dangerous': True,
                        'reason': f'高危文件类型: {ext}',
                        'size': size,
                    })
                    break
            else:
                # 2. 检查双重扩展名伪装
                if self.DOUBLE_EXTENSION_PATTERN.search(filename_lower):
                    match = self.DOUBLE_EXTENSION_PATTERN.search(filename_lower)
                    suspicious.append({
                        'filename': filename,
                        'dangerous': True,
                        'reason': f'双重扩展名伪装: {match.group(0)}',
                        'size': size,
                    })

                # 3. 检查可疑扩展名 + 异常大小
                elif any(filename_lower.endswith(ext) for ext in self.SUSPICIOUS_EXTENSIONS):
                    # 零大小文件可疑
                    if size == 0:
                        suspicious.append({
                            'filename': filename,
                            'dangerous': False,
                            'reason': '文件大小为0，可能为占位攻击文件',
                            'size': size,
                        })
                    # 超大压缩包
                    elif size > 50 * 1024 * 1024:  # >50MB
                        suspicious.append({
                            'filename': filename,
                            'dangerous': False,
                            'reason': f'压缩包过大({size/1024/1024:.1f}MB)，可能包含恶意载荷',
                            'size': size,
                        })

        return {'suspicious': suspicious}

    def _is_suspicious_url(self, url: str) -> bool:
        """判断 URL 是否可疑"""
        url_lower = url.lower()

        # 短链接服务
        short_services = [
            'bit.ly', 'tinyurl.com', 't.co', 'ow.ly',
            'is.gd', 'buff.ly', 'goo.gl', 'short.link',
            'rb.gy', 'cutt.ly', 'short.ly',
        ]
        for service in short_services:
            if service in url_lower:
                return True

        # URL 中包含可疑关键词
        suspicious_patterns = [
            r'login', r'signin', r'verify', r'confirm',
            r'update', r'secure', r'account', r'password',
            r'bank', r'paypal', r'apple', r'microsoft',
        ]
        path_query = url_lower.split('?', 1)
        for pattern in suspicious_patterns:
            if pattern in path_query[0]:
                return True

        # @ 符号（URL 认证伪装）
        if '@' in url_lower:
            return True

        return False

    def _is_suspicious_domain(self, email: str) -> bool:
        """判断发件人域名是否可疑"""
        if '@' not in email:
            return False

        domain = email.split('@')[1].lower()

        # 常见免费邮箱（容易被滥用但本身不可疑）
        free_providers = {
            'gmail.com', 'yahoo.com', 'hotmail.com',
            'outlook.com', '163.com', 'qq.com',
            '126.com', 'sina.com', 'sohu.com',
        }

        if domain in free_providers:
            return False

        # 知名品牌域名仿冒检测
        brand_domains = {
            'paypal': 'paypal.com',
            'apple': 'apple.com',
            'microsoft': 'microsoft.com',
            'google': 'google.com',
            'amazon': 'amazon.com',
            'facebook': 'facebook.com',
            'alibaba': 'alibaba.com',
            'taobao': 'taobao.com',
        }

        for brand, official in brand_domains.items():
            if brand in domain and domain != official:
                # 如 paypal-security.com 非 paypal.com
                return True

        return False