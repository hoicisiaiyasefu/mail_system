# -*- coding: utf-8 -*-
"""
链接分析模块
检测恶意链接：短链接展开、域名仿冒、重定向检测
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)


class LinkAnalyzer:
    """链接分析器"""

    # 已知恶意域名库（示例）
    KNOWN_MALICIOUS_DOMAINS = {
        'phishing.example.com',
        'malware.test.net',
        'scam.site.org',
    }

    # 短链接服务列表
    SHORT_URL_SERVICES = {
        'bit.ly', 'tinyurl.com', 't.co', 'ow.ly',
        'is.gd', 'buff.ly', 'goo.gl', 'cutt.ly',
        'rb.gy', 'short.link', 'bc.vc', 'lnkd.in',
        'shorte.st', 'adf.ly', 'tiny.cc', 'qr.ae',
        'short.ly', 'v.gd', 'x.co', 'yourls.org',
    }

    # 域名仿冒模式
    TYPOSQUATTING_PATTERNS = {
        # 品牌 -> 常见仿冒变形
        'paypal': ['paypaI', 'paypall', 'paypa1', 'paypai', 'pay-pol'],
        'microsoft': ['micr0soft', 'micros0ft', 'microsoftt', 'mircosoft', 'micrsoft'],
        'apple': ['appIe', 'app1e', 'appe', 'apple-id', 'appleid'],
        'google': ['googIe', 'go0gle', 'goog1e', 'g00gle', 'googles'],
        'amazon': ['amaz0n', 'amaz0n', 'amaznn', 'arnazon'],
        'facebook': ['faceb00k', 'facebok', 'face-book'],
        'dropbox': ['dr0pbox', 'dropb0x', 'dorpbox'],
        'alibaba': ['alibab', 'alibba', 'ali-baba'],
        'wechat': ['wechart', 'we-chat'],
        'taobao': ['ta0bao', 'taoboa', 'tao-bao'],
    }

    # 疑似恶意 URL 关键词
    MALICIOUS_URL_PATTERNS = [
        r'\.tk$',       # 免费顶级域名（常被滥用）
        r'\.ml$',
        r'\.ga$',
        r'\.cf$',
        r'\.bond$',
        r'\.xyz$',
        r'\.top$',
        r'\.loan$',
        r'\.work$',
        r'\.click$',
    ]

    def __init__(self, expand_short_urls: bool = True):
        self.expand_short_urls = expand_short_urls

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本中的所有链接
        Returns:
            {
                'all_urls': list,
                'malicious': [{'url': str, 'reason': str}],
                'suspicious': [{'url': str, 'reason': str}],
                'short_urls': list,
                'redirect_urls': list,
            }
        """
        url_pattern = re.compile(
            r'https?://[^\s<>"\'{}\|\\^`\[\]]+|'
            r'(?:www\.)[^\s<>"\'{}\|\\^`\[\]]+',
            re.IGNORECASE
        )

        urls = url_pattern.findall(text)
        urls = [u.strip().rstrip('.,;:!?）)') for u in urls]

        # 去重
        seen = set()
        unique_urls = []
        for url in urls:
            url_normalized = url.lower().rstrip('/')
            if url_normalized not in seen:
                seen.add(url_normalized)
                unique_urls.append(url)

        malicious = []
        suspicious = []
        short_urls = []
        redirect_urls = []

        for url in unique_urls:
            # 分析每个 URL
            threat_level, reason = self._classify_url(url)

            if threat_level == 'malicious':
                malicious.append({
                    'url': url,
                    'reason': reason,
                })
            elif threat_level == 'suspicious':
                suspicious.append({
                    'url': url,
                    'reason': reason,
                })

            # 检测短链接
            if self._is_short_url(url):
                short_urls.append({
                    'url': url,
                    'expanded': None,  # 实际展开需要网络请求
                })

            # 检测重定向
            redirect_target = self._detect_redirect(url)
            if redirect_target:
                redirect_urls.append({
                    'url': url,
                    'redirects_to': redirect_target,
                    'suspicious': self._is_redirect_suspicious(url, redirect_target),
                })

        return {
            'all_urls': unique_urls,
            'malicious': malicious,
            'suspicious': suspicious,
            'short_urls': short_urls,
            'redirect_urls': redirect_urls,
            'total_count': len(unique_urls),
            'threat_count': len(malicious) + len(suspicious),
        }

    def _classify_url(self, url: str) -> Tuple[str, str]:
        """
        分类 URL 威胁等级
        Returns:
            ('malicious'|'suspicious'|'safe', reason)
        """
        url_lower = url.lower()

        # 尝试解析 URL
        parsed = None
        try:
            if not url_lower.startswith('http'):
                url_lower = 'http://' + url_lower
            parsed = urlparse(url_lower)
        except Exception:
            return 'suspicious', '无法解析的URL格式'

        if not parsed or not parsed.netloc:
            return 'suspicious', '缺少有效域名'

        domain = parsed.netloc.lower()

        # 1. 检查已知恶意域名
        if domain in self.KNOWN_MALICIOUS_DOMAINS:
            return 'malicious', f'已知恶意域名: {domain}'

        # 2. IP 地址形式
        ip_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        if ip_pattern.match(domain):
            return 'suspicious', '使用IP地址而非域名，可能隐藏真实来源'

        # 3. 可疑顶级域名
        for pattern in self.MALICIOUS_URL_PATTERNS:
            if re.search(pattern, domain):
                return 'suspicious', f'使用高风险顶级域名: {domain}'

        # 4. 域名仿冒检测
        for brand, typos in self.TYPOSQUATTING_PATTERNS.items():
            if brand in domain and domain != f"www.{brand}.com" and \
               domain != f"{brand}.com":
                # 检查是否为仿冒域名
                for typo in typos:
                    if typo.lower() in domain:
                        return 'suspicious', f'疑似仿冒{brand}域名: {domain}'

            # 域名中包含品牌名但不是官方域名
            official_domains = {
                'paypal': ['paypal.com'],
                'microsoft': ['microsoft.com'],
                'apple': ['apple.com', 'icloud.com'],
                'google': ['google.com', 'googleapis.com'],
                'amazon': ['amazon.com', 'aws.amazon.com'],
                'facebook': ['facebook.com', 'fb.com'],
                'alibaba': ['alibaba.com', 'aliexpress.com'],
                'taobao': ['taobao.com'],
            }

            official = official_domains.get(brand, [])
            if brand in domain and not any(d in domain for d in official):
                return 'suspicious', f'域名包含{brand}但非官方域名: {domain}'

        # 5. URL 中包含 @ 符号（认证伪装）
        if '@' in url_lower and '://' in url_lower:
            # http://trusted.com@evil.com 形式
            return 'malicious', 'URL包含@符号，可能是认证伪装攻击'

        # 6. URL 编码过长（混淆）
        decoded = unquote(parsed.path) if hasattr(unquote, '__call__') else url_lower
        if '?' in url_lower:
            query = url_lower.split('?', 1)[1]
            # 过长查询参数
            if len(query) > 500:
                return 'suspicious', 'URL查询参数过长，可能包含隐藏数据'

        # 7. 非标准端口
        if parsed.port and parsed.port not in (80, 443, 8080, 8443):
            return 'suspicious', f'使用非标准端口: {parsed.port}'

        return 'safe', ''

    def _is_short_url(self, url: str) -> bool:
        """判断是否为短链接"""
        for service in self.SHORT_URL_SERVICES:
            if service in url.lower():
                return True
        return False

    def _detect_redirect(self, url: str) -> Optional[str]:
        """
        检测 URL 中的重定向目标
        不实际发送请求，仅通过 URL 参数分析
        """
        url_lower = url.lower()

        # 常见重定向参数
        redirect_params = [
            'redirect', 'redirect_url', 'redirect_uri',
            'url', 'target', 'goto', 'return',
            'next', 'dest', 'destination', 'to',
            'callback', 'returnurl', 'redir',
        ]

        parsed = urlparse(url_lower)
        query_params = parsed.query

        for param in redirect_params:
            pattern = re.compile(
                r'[?&]' + re.escape(param) + r'=([^&]+)',
                re.IGNORECASE
            )
            match = pattern.search('?' + query_params)
            if match:
                target = match.group(1)
                # 检查是否为 URL
                if target.startswith('http') or target.startswith('//'):
                    return target

        return None

    def _is_redirect_suspicious(self, source: str, target: str) -> bool:
        """判断重定向目标是否可疑"""
        try:
            source_domain = urlparse(source).netloc
            target_domain = urlparse(target).netloc

            # 同域名重定向=安全
            if source_domain == target_domain:
                return False

            # 不同域名重定向=可疑
            return True
        except Exception:
            return True

    def extract_urls(self, text: str) -> List[str]:
        """从文本中提取所有 URL"""
        result = self.analyze(text)
        return result['all_urls']