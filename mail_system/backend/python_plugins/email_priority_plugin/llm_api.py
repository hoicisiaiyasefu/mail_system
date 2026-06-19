# -*- coding: utf-8 -*-
"""
优先级引擎大模型接口（薄封装层）
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
    """优先级引擎 LLM 服务（兼容共享/独立两种模式）"""

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

    # -------- 优先级领域方法 --------
    def analyze_priority(self, email_data: Dict[str, Any],
                           user_context: str = "") -> Dict[str, Any]:
        """
        调用 LLM 分析邮件优先级
        """
        if not self._provider or not self._provider.api_key:
            return {'priority_score': 50, 'reason': 'LLM 未配置'}

        prompt = f"""请分析以下邮件的紧急程度和重要性，给出 0-100 的优先级分数。

发件人：{email_data.get('from', '')}
主题：{email_data.get('subject', '')}
内容摘要：{email_data.get('content', '')[:1000]}

用户画像：{user_context or '普通用户'}

请以 JSON 格式返回：
{{"priority_score": 75, "priority_level": "high/medium/low", "reason": "简短理由"}}"""

        try:
            resp = self.chat(prompt, "你是邮件管理助手，请严格以 JSON 格式回复。")
            import json
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("```")[1]
                if resp.startswith("json"):
                    resp = resp[4:]
            return json.loads(resp)
        except Exception:
            return {'priority_score': 50, 'priority_level': 'medium', 'reason': 'LLM 响应解析失败'}