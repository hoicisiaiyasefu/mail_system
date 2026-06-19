#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件安全分析桥接脚本
通过命令行参数接收 JSON 邮件数据，调用 SecurityEngine 处理

用法:
  python bridge_security.py '<json_email_data>'                               # 无配置
  python bridge_security.py '<json_email_data>' '<json_config>'               # 有配置
"""

import sys
import json
import os

# ============================================================
# 彻底抑制 stderr：Java 端 redirectErrorStream(true) 会将
# stderr 合并到 stdout，任何 stderr 输出都会污染 JSON 结果。
# 必须在所有 import 之前执行，防止三方库注册了 handler。
# ============================================================
_devnull_fd = os.open(os.devnull, os.O_WRONLY)
_original_stderr_fd = os.dup(2)
os.dup2(_devnull_fd, 2)
os.close(_devnull_fd)

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