# -*- coding: utf-8 -*-
"""
统一大模型 SDK 服务提供商基类
继承常见的 LLM 服务商 SDK，提供可插拔的大模型调用能力。

使用方式：
  1. 在 application.yml 中配置 llm.enabled, llm.api_key 等
  2. 各插件通过 PluginRegistry 获取 LLMProvider 实例
  3. 若未配置 API Key，自动降级为纯规则/本地模型模式

支持的提供商（通过 pip 安装）：
  - openai      → openai 官方 Python SDK
  - custom      → 兼容 OpenAI API 的自定义服务（vLLM/Ollama 等），使用 urllib 兜底

设计原则：
  - 用户自行决定是否填写 API Key 开启功能
  - 未填写时优雅降级，不影响基础邮件功能
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


# ============================================================
# 尝试导入 OpenAI SDK，失败则使用纯 HTTP 客户端
# ============================================================

_HAS_OPENAI_SDK = False
_openai_module: Any = None
try:
    import openai as _openai_module  # type: ignore
    _HAS_OPENAI_SDK = True
except ImportError:
    _openai_module = None


# ============================================================
# 抽象基类
# ============================================================

class BaseLLMProvider(ABC):
    """大模型服务提供商抽象基类"""

    def __init__(self,
                 api_key: str,
                 provider: str = "openai",
                 model: str = "gpt-3.5-turbo",
                 base_url: Optional[str] = None):
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.base_url = base_url or self._default_base_url()
        self._connected = False

    def _default_base_url(self) -> str:
        if self.provider == "openai":
            return "https://api.openai.com/v1"
        return "https://api.openai.com/v1"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    def test_connection(self) -> bool:
        """测试 API 连接"""
        ...

    @abstractmethod
    def chat(self,
             messages: List[Dict[str, str]],
             max_tokens: int = 200,
             temperature: float = 0.3) -> str:
        """调用聊天模型（底层接口）"""
        ...

    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        ...

    # ============================================================
    # 领域方法：各插件可直接调用
    # ============================================================

    def analyze(self, prompt: str, max_tokens: int = 200,
                system_prompt: str = "你是一个邮件分析助手。请简洁地回答。") -> str:
        """
        通用分析接口（兼容旧版 API）
        Args:
            prompt: 用户提示词
            max_tokens: 最大 token 数
            system_prompt: 系统提示词
        Returns:
            模型输出文本
        """
        return self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )

    def detect_malicious_intent(self, content: str,
                                 links: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        深度学习检测恶意意图（安全引擎专用）
        分析内容包括：钓鱼、诈骗、社会工程学攻击、恶意链接等
        """
        links_text = '\n'.join(links) if links else '无链接'
        prompt = (
            f"作为邮件安全专家，分析以下邮件是否包含恶意意图：\n\n"
            f"邮件内容:\n{content[:1500]}\n\n"
            f"包含的链接:\n{links_text}\n\n"
            f"请判断是否包含：钓鱼、诈骗、恶意软件分发、社会工程学攻击、"
            f"勒索软件、商业邮件诈骗(BEC)等威胁。\n"
            f"回复格式：\n"
            f"- 如果安全，回复'安全'\n"
            f"- 如果可疑，回复'可疑: [具体威胁类型] - [详细分析]'"
        )
        result = self.analyze(prompt, max_tokens=200,
                               system_prompt="你是一个邮件安全分析专家。请用中文简洁回答。")
        malicious = '可疑' in result

        risk_type = '未知'
        for kw, rt in [('钓鱼', '钓鱼攻击'), ('诈骗', '诈骗'), ('恶意软件', '恶意软件'),
                        ('勒索', '勒索软件'), ('社会工程', '社会工程学攻击'),
                        ('BEC', '商业邮件诈骗'), ('商业邮件诈骗', '商业邮件诈骗')]:
            if kw in result:
                risk_type = rt
                break

        return {
            'malicious': malicious,
            'risk_type': risk_type if malicious else '无',
            'reason': result,
        }

    def analyze_spoof_attempt(self, from_email: str, content: str) -> Dict[str, Any]:
        """
        深度分析是否伪造发件人（安全引擎专用）
        """
        prompt = (
            f"分析以下邮件是否伪造发件人身份：\n"
            f"发件人地址: {from_email}\n"
            f"邮件内容: {content[:800]}\n\n"
            f"判断标准：内容与发件人身份是否一致？语言风格是否符合该身份？"
            f"是否有索要敏感信息的行为？\n"
            f"回复'可信'或'可疑: [原因]'"
        )
        result = self.analyze(prompt, max_tokens=150,
                               system_prompt="你是一个邮件安全分析专家。请用中文简洁回答。")
        suspicious = '可疑' in result
        return {
            'suspicious': suspicious,
            'reason': result,
        }

    def detect_spoofing(self, content: str, from_email: str) -> Dict[str, Any]:
        """
        检测潜在伪造发件人（优先级引擎专用）
        """
        prompt = (
            f"分析以下邮件内容与其发件人身份是否一致：\n"
            f"发件人: {from_email}\n"
            f"内容: {content[:800]}\n\n"
            f"如果内容看起来与该发件人身份不符（例如银行邮箱发推广广告），"
            f"请回复'可疑'并给出理由。否则回复'正常'。"
        )
        result = self.analyze(prompt, max_tokens=100)
        suspicious = '可疑' in result
        return {
            'suspicious': suspicious,
            'reason': result,
        }

    def generate_summary(self, content: str, max_length: int = 100) -> str:
        """
        生成邮件摘要（优先级引擎专用）
        """
        prompt = (
            f"请用不超过{max_length}字总结以下邮件内容，"
            f"包含发件人意图和关键信息：\n\n{content[:2000]}"
        )
        return self.analyze(prompt, max_tokens=max_length * 2)


# ============================================================
# OpenAI SDK 实现（优先使用）
# ============================================================

class OpenAIProvider(BaseLLMProvider):
    """
    基于 OpenAI 官方 SDK 的实现
    需要: pip install openai
    """

    def __init__(self,
                 api_key: str,
                 provider: str = "openai",
                 model: str = "gpt-3.5-turbo",
                 base_url: Optional[str] = None):
        super().__init__(api_key, provider, model, base_url)
        self._client = None

    def test_connection(self) -> bool:
        if _openai_module is None:
            return False
        try:
            self._client = _openai_module.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url.rstrip('/'),
            )
            # 发送最小请求验证连接
            self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            self._connected = True
            logger.info(f"OpenAI SDK 连接成功: {self.provider}/{self.model}")
            return True
        except Exception as e:
            logger.warning(f"OpenAI SDK 连接失败: {e}")
            self._connected = False
            return False

    def chat(self,
             messages: List[Dict[str, str]],
             max_tokens: int = 200,
             temperature: float = 0.3) -> str:
        if not self._connected or not self._client:
            return ""
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip() if resp.choices else ""
        except Exception as e:
            logger.error(f"OpenAI SDK 调用失败: {e}")
            return ""

    def close(self) -> None:
        self._client = None
        self._connected = False
        logger.info("OpenAI SDK 连接已关闭")


# ============================================================
# HTTP 兼容实现（兜底方案，无 SDK 依赖）
# ============================================================

class HttpLLMProvider(BaseLLMProvider):
    """
    基于纯 HTTP 请求的实现（无需额外 pip 安装）
    兼容所有 OpenAI 兼容 API（vLLM、Ollama、LM Studio 等）
    """

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'MailSystem/1.0',
            }
            payload = json.dumps({
                'model': self.model,
                'messages': [{'role': 'user', 'content': 'ping'}],
                'max_tokens': 5,
            }).encode('utf-8')

            req = Request(url, data=payload, headers=headers, method='POST')
            urlopen(req, timeout=10).read()
            self._connected = True
            logger.info(f"HTTP LLM 连接成功: {self.provider}/{self.model}")
            return True
        except Exception as e:
            logger.warning(f"HTTP LLM 连接失败: {e}")
            self._connected = False
            return False

    def chat(self,
             messages: List[Dict[str, str]],
             max_tokens: int = 200,
             temperature: float = 0.3) -> str:
        if not self._connected:
            return ""
        try:
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'MailSystem/1.0',
            }
            payload = json.dumps({
                'model': self.model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
            }).encode('utf-8')

            req = Request(url, data=payload, headers=headers, method='POST')
            resp = urlopen(req, timeout=45)
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        except Exception as e:
            logger.error(f"HTTP LLM 调用失败: {e}")
            return ""

    def close(self) -> None:
        self._connected = False
        logger.info("HTTP LLM 连接已关闭")


# ============================================================
# 工厂函数
# ============================================================

def create_llm_provider(api_key: str,
                        provider: str = "openai",
                        model: str = "gpt-3.5-turbo",
                        base_url: Optional[str] = None,
                        prefer_sdk: bool = True) -> Optional[BaseLLMProvider]:
    """
    创建 LLM 服务提供商实例

    Args:
        api_key:  API 密钥（空字符串则不创建）
        provider: 服务商类型 ('openai', 'custom')
        model:    模型名称
        base_url: 自定义 API 地址
        prefer_sdk: 是否优先使用 OpenAI SDK

    Returns:
        BaseLLMProvider 实例，API Key 为空时返回 None
    """
    api_key = (api_key or "").strip()
    if not api_key:
        logger.info("未配置 LLM API Key，大模型功能已禁用")
        return None

    if prefer_sdk and _HAS_OPENAI_SDK:
        logger.info(f"使用 OpenAI SDK: {provider}/{model}")
        return OpenAIProvider(api_key, provider, model, base_url)
    else:
        logger.info(f"使用 HTTP 客户端: {provider}/{model}")
        return HttpLLMProvider(api_key, provider, model, base_url)