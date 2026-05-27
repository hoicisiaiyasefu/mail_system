#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全检测桥接脚本
通过命令行参数接收 JSON 邮件数据，调用 SecurityEngine 处理

用法:
  python bridge_security.py '<json_email_data>'                          # 无 LLM
  python bridge_security.py '<json_email_data>' '<json_config>'           # 有配置
"""

import sys
import json
import os

# 确保能找到同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugin_registry import init_registry


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "缺少邮件数据参数"}))
        sys.exit(1)

    try:
        email_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON 解析失败(邮件数据): {str(e)}"}))
        sys.exit(1)

    # 可选的配置文件/JSON 参数
    config_dict = None
    if len(sys.argv) >= 3:
        try:
            arg2 = sys.argv[2]
            if arg2.endswith('.json'):
                config_dict = {"plugins": {"security_ai_plugin": {"enabled": True}}, "llm": {"enabled": False}}
            else:
                config_dict = json.loads(arg2)
        except (json.JSONDecodeError, Exception):
            pass

    try:
        registry = init_registry(config_dict=config_dict)
    except Exception as e:
        print(json.dumps({"error": f"插件注册表初始化失败: {str(e)}"}))
        sys.exit(1)

    result = registry.process("security_ai_plugin", email_data)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()