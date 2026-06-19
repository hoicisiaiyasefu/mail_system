# -*- coding: utf-8 -*-
"""
插件注册表
统一管理所有 Python 插件的生命周期与 LLM 实例共享。

职责：
  1. 插件发现与注册（从配置中读入启用的插件列表）
  2. LLM 实例统一创建与注入（所有插件共享同一 LLM 连接）
  3. 插件配置分发
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# 确保插件目录在 sys.path
_PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from llm_sdk_provider import BaseLLMProvider, create_llm_provider

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    插件注册表（单例）

    使用方式：
        registry = PluginRegistry.get_instance()
        registry.load_config("path/to/config.json")
        registry.init_plugins()
        result = registry.process("email_priority_plugin", email_data)
    """

    _instance: Optional["PluginRegistry"] = None

    def __init__(self):
        self._plugins: Dict[str, Any] = {}           # plugin_name → plugin instance
        self._llm_provider: Optional[BaseLLMProvider] = None
        self._config: Dict[str, Any] = {}
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """仅测试用：清除单例"""
        if cls._instance:
            cls._instance.shutdown()
            cls._instance = None

    # ============================================================
    # 配置加载
    # ============================================================

    def load_config(self, config_path: str) -> None:
        """
        从 JSON 配置文件加载插件配置

        配置文件格式（参见 application.yml 中 plugins.config_file 指向的文件）：
        {
          "llm": {
            "enabled": true,
            "api_key": "sk-xxx",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "base_url": "https://api.openai.com/v1"
          },
          "plugins": {
            "email_priority_plugin": {
              "enabled": true,
              "data_dir": "./data",
              ...
            },
            "security_ai_plugin": {
              "enabled": true,
              "enable_link_expand": true,
              ...
            },
            "spam_ml_plugin": {
              "enabled": true,
              "model_dir": "./models",
              ...
            }
          }
        }
        """
        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            self._config = self._default_config()
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
        logger.info(f"已加载插件配置: {config_path}")

    def load_config_dict(self, config: Dict[str, Any]) -> None:
        """直接从字典加载配置（Java 端传入）"""
        self._config = config or self._default_config()
        logger.info("已从字典加载插件配置")

    def _default_config(self) -> Dict[str, Any]:
        return {
            "llm": {"enabled": False},
            "plugins": {},
        }

    # ============================================================
    # 初始化
    # ============================================================

    def init_plugins(self) -> bool:
        """
        初始化所有已启用的插件
        必须在 load_config 之后调用
        """
        if self._initialized:
            return True

        try:
            # 1. 初始化 LLM
            self._init_llm()

            # 2. 发现并加载插件
            plugin_configs = self._config.get("plugins", {})
            for plugin_name, plugin_cfg in plugin_configs.items():
                if not plugin_cfg.get("enabled", True):
                    logger.info(f"插件已禁用: {plugin_name}")
                    continue

                self._load_plugin(plugin_name, plugin_cfg)

            self._initialized = True
            logger.info(f"插件注册表初始化完成, LLM: {'已启用' if self._llm_provider else '未启用'}")
            return True

        except Exception as e:
            logger.error(f"插件注册表初始化失败: {e}", exc_info=True)
            return False

    def _init_llm(self) -> None:
        """根据配置初始化共享 LLM"""
        llm_cfg = self._config.get("llm", {})
        if not llm_cfg.get("enabled", False):
            logger.info("LLM 功能已禁用（配置中 llm.enabled=false）")
            return

        self._llm_provider = create_llm_provider(
            api_key=llm_cfg.get("api_key", ""),
            provider=llm_cfg.get("provider", "openai"),
            model=llm_cfg.get("model", "gpt-3.5-turbo"),
            base_url=llm_cfg.get("base_url"),
        )

        if self._llm_provider:
            connected = self._llm_provider.test_connection()
            if not connected:
                logger.warning("LLM 连接失败，大模型功能不可用")
                self._llm_provider = None
        else:
            logger.info("未配置 API Key，大模型功能已禁用")

    def _load_plugin(self, plugin_name: str, plugin_config: Dict[str, Any]) -> None:
        """
        动态加载插件模块
        约定：插件目录名为 plugin_name，引擎类在主模块的 engine 属性中
        """
        try:
            # 尝试导入插件模块
            # 例如: email_priority_plugin → email_priority_plugin.priority_engine.PriorityEngine
            module_mapping = {
                "email_priority_plugin": ("email_priority_plugin.priority_engine", "PriorityEngine"),
                "security_ai_plugin": ("security_ai_plugin.security_engine", "SecurityEngine"),
                "spam_ml_plugin": ("spam_ml_plugin.ml_spam_detector", "MLSpamDetector"),
            }

            module_path, class_name = module_mapping.get(plugin_name, (None, None))
            if not module_path or not class_name:
                logger.warning(f"未知插件: {plugin_name}")
                return

            import importlib
            module = importlib.import_module(module_path)
            engine_class = getattr(module, class_name)

            # 注入 LLM provider
            plugin_config = dict(plugin_config)
            plugin_config["_llm_provider"] = self._llm_provider

            instance = engine_class()
            if not instance.init(plugin_config):
                logger.error(f"插件初始化失败: {plugin_name}")
                return

            self._plugins[plugin_name] = instance
            logger.info(f"插件已加载: {plugin_name} ({class_name})")

        except Exception as e:
            logger.error(f"加载插件失败 {plugin_name}: {e}", exc_info=True)

    # ============================================================
    # 运行时接口
    # ============================================================

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """获取已加载的插件实例"""
        return self._plugins.get(plugin_name)

    def get_llm(self) -> Optional[BaseLLMProvider]:
        """获取共享 LLM 实例"""
        return self._llm_provider

    def process(self, plugin_name: str, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用指定插件处理邮件

        Returns:
            处理结果字典，若插件未加载则返回错误信息
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return {
                "plugin_name": plugin_name,
                "error": f"插件未加载: {plugin_name}",
            }
        try:
            return plugin.process(email_data)
        except Exception as e:
            logger.error(f"插件执行异常 {plugin_name}: {e}", exc_info=True)
            return {
                "plugin_name": plugin_name,
                "error": str(e),
            }

    def process_all(self, email_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        调用所有已加载插件处理邮件

        Returns:
            {plugin_name: result_dict, ...}
        """
        results = {}
        for plugin_name in self._plugins:
            results[plugin_name] = self.process(plugin_name, email_data)
        return results

    def list_plugins(self) -> List[str]:
        """列出所有已加载的插件名称"""
        return list(self._plugins.keys())

    # ============================================================
    # 生命周期
    # ============================================================

    def shutdown(self) -> None:
        """关闭所有插件和 LLM 连接"""
        for plugin_name, plugin in self._plugins.items():
            try:
                if hasattr(plugin, 'shutdown'):
                    plugin.shutdown()
            except Exception as e:
                logger.warning(f"插件关闭异常 {plugin_name}: {e}")

        if self._llm_provider:
            self._llm_provider.close()
            self._llm_provider = None

        self._plugins.clear()
        self._initialized = False
        logger.info("插件注册表已关闭")


# ============================================================
# 便捷函数（供 bridge 脚本和 pipeline 使用）
# ============================================================

def init_registry(config_path: Optional[str] = None,
                  config_dict: Optional[Dict[str, Any]] = None) -> PluginRegistry:
    """
    初始化插件注册表的便捷函数

    用法:
        registry = init_registry(config_path="./plugins_config.json")
        # 或
        registry = init_registry(config_dict={"llm": {...}, "plugins": {...}})
    """
    registry = PluginRegistry.get_instance()
    if config_dict:
        registry.load_config_dict(config_dict)
    elif config_path:
        registry.load_config(config_path)
    else:
        # 尝试自动发现配置文件
        default_path = os.path.join(_PARENT_DIR, "plugins_config.json")
        registry.load_config(default_path)

    registry.init_plugins()
    return registry