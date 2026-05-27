# -*- coding: utf-8 -*-
"""
安全引擎大模型接口（薄封装层）
通过 PluginRegistry 注入共享 LLM 实例或独立创建。

用法：
  共享模式（推荐）：   LLMServiceProvider(_shared_provider=registry.get_llm())
  独立模式（测试）：   LLMServiceProvider(api_key="sk-xxx", provider="openai")
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# 确保能找到上级目录的公共模块
_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from llm_sdk_provider import (
    BaseLLMProvider,
    HttpLLMProvider,
    OpenAIProvider,
    create_llm_provider,
)

logger = logging.getLogger(__name__)


class LLMServiceProvider:
    """安全检测 LLM 服务（兼容共享/独立两种模式）"""

    def __init__(self,
                 api_key: str = "",
                 provider: str = "openai",
                 model: str = "gpt-3.5-turbo",
                 base_url: Optional[str] = None,
                 _shared_provider: Optional[BaseLLMProvider] = None):
        """
        Args:
            api_key:    LLM API Key（独立模式）
            provider:   LLM 提供商（独立模式）
            model:      模型名称（独立模式）
            base_url:   自定义 API URL（独立模式）
            _shared_provider: PluginRegistry 注入的共享 LLM 实例（共享模式）
        """
        if _shared_provider is not None:
            self._provider: Optional[BaseLLMProvider] = _shared_provider
        else:
            self._provider = create_llm_provider(
                api_key=api_key,
                provider=provider,
                model=model,
                base_url=base_url,
            )

    # -------- 委托属性 --------
    @property
    def api_key(self):
        return self._provider.api_key if self._provider else ""

    @property
    def model(self):
        return self._provider.model if self._provider else ""

    @property
    def is_connected(self) -> bool:
        return self._provider is not None and self._provider.is_connected

    def test_connection(self) -> bool:
        if not self._provider:
            return False
        return self._provider.test_connection()

    def chat(self, prompt: str, system_prompt: str = "") -> str:
        if not self._provider:
            return ""
        return self._provider.analyze(prompt=prompt, system_prompt=system_prompt)

    def close(self):
        if self._provider:
            self._provider.close()

    # -------- 安全领域方法 --------
    def detect_malicious_intent(self, content: str,
                                  links: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        调用 LLM 分析内容是否存在恶意意图（钓鱼、诈骗等）
        """
        if not self._provider or not self._provider.api_key:
            return {'malicious': False, 'reason': 'LLM 未配置'}

        links_text = '\n'.join(links) if links else '无'
        prompt = f"""分析以下邮件内容是否包含恶意意图（钓鱼、诈骗、社会工程学攻击等）。

邮件内容：
{content[:2000]}

包含的链接：
{links_text}

请以 JSON 格式返回：
{{"malicious": true/false, "risk_type": "phishing/spam/scam/none", "reason": "简短理由"}}"""

        try:
            resp = self.chat(prompt, "你是邮件安全分析专家，请严格以 JSON 格式回复。")
            import json
            # 尝试解析 JSON
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("```")[1]
                if resp.startswith("json"):
                    resp = resp[4:]
            return json.loads(resp)
        except Exception:
            return {'malicious': False, 'risk_type': 'parse_error', 'reason': 'LLM 响应解析失败'}

    def analyze_attachments(self, attachments: List[Dict]) -> Dict[str, Any]:
        """
        分析附件列表是否可疑
        """
        if not attachments:
            return {'suspicious': [], 'safe': []}

        suspicious = []
        safe = []

        for att in attachments:
            filename = att.get('filename', '')
            ext = os.path.splitext(filename)[1].lower() if filename else ''

            # 危险扩展名
            dangerous_exts = {'.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.scr', '.pif'}
            suspicious_exts = {'.zip', '.rar', '.7z', '.iso', '.docm', '.xlsm', '.pptm'}

            if ext in dangerous_exts:
                suspicious.append({
                    'filename': filename,
                    'dangerous': True,
                    'reason': f'可执行文件: {ext}',
                })
            elif ext in suspicious_exts:
                suspicious.append({
                    'filename': filename,
                    'dangerous': False,
                    'reason': f'潜在风险文件: {ext}',
                })
            else:
                safe.append({'filename': filename})

        return {'suspicious': suspicious, 'safe': safe}