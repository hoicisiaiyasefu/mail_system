#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾邮件检测桥接脚本（增强版）
通过命令行参数接收 JSON 邮件数据，调用 MLSpamDetector + LLM 双重判断

用法:
  python bridge_spam.py '<json_email_data>'                               # 无配置（纯 ML）
  python bridge_spam.py '<json_email_data>' '<json_config>'               # 有配置（ML + LLM）
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


def llm_spam_judge(llm, email_data: dict):
    """
    使用大模型进行垃圾邮件二次判断
    返回: dict 或 None（LLM 不可用时）
    """
    if llm is None or not llm.is_connected:
        return None

    subject = email_data.get('subject', '')
    content = email_data.get('content', '')
    from_addr = email_data.get('from', '')

    prompt = (
        f"请判断以下邮件是否为垃圾邮件（垃圾邮件包括：广告推销、诈骗钓鱼、"
        f"虚假中奖、赌博色情、代办发票、刷单兼职等）。\n\n"
        f"发件人：{from_addr}\n"
        f"主题：{subject}\n"
        f"正文：{content[:1500]}\n\n"
        f"请回复 JSON 格式（不要包含其他内容）：\n"
        f'{{"is_spam": true或false, "score": 0.0到1.0之间的浮点数, "reason": "简短判断理由"}}'
    )

    try:
        response = llm.chat(
            messages=[
                {"role": "system", "content": "你是一个专业的垃圾邮件检测专家。请严格按照 JSON 格式回复，不要包含其他内容。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.1,
        )

        # 尝试从回复中提取 JSON
        response = response.strip()
        # 移除可能的 markdown 代码块标记
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

        result = json.loads(response)
        return {
            "is_spam": bool(result.get("is_spam", False)),
            "spam_score": float(result.get("score", 0.5)),
            "reason": str(result.get("reason", "")),
        }
    except (json.JSONDecodeError, Exception):
        # JSON 解析失败，尝试从文本中推断
        response_lower = ""
        try:
            response_lower = response.lower()
        except Exception:
            pass
        if any(kw in response_lower for kw in ['spam', '垃圾', '是', 'yes', 'true']):
            if not any(kw in response_lower for kw in ['not spam', '不是垃圾', '正常', '不是', 'no', 'false']):
                return {
                    "is_spam": True,
                    "spam_score": 0.7,
                    "reason": "LLM 文本推断为垃圾邮件",
                }
        return None  # 无法判断，回退到 ML 结果


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
                # 配置文件路径 — 保持基本配置
                config_dict = {
                    "plugins": {"spam_ml_plugin": {"enabled": True}},
                    "llm": {"enabled": False}
                }
            else:
                config_dict = json.loads(arg2)
        except (json.JSONDecodeError, Exception):
            pass

    try:
        registry = init_registry(config_dict=config_dict)
    except Exception as e:
        print(json.dumps({"error": f"插件注册表初始化失败: {str(e)}"}))
        sys.exit(1)

    # 1. ML 模型检测（主力）
    ml_result = registry.process("spam_ml_plugin", email_data)
    if "error" in ml_result:
        print(json.dumps(ml_result, ensure_ascii=False))
        sys.exit(1)

    ml_is_spam = bool(ml_result.get("is_spam", False))
    ml_score = float(ml_result.get("spam_score", 0.0))
    ml_confidence = float(ml_result.get("confidence", 0.0))

    # 2. LLM 二次判断（辅助，仅在 LLM 可用时启用）
    llm = registry.get_llm()
    llm_result = llm_spam_judge(llm, email_data)

    # 3. 综合判定
    if llm_result is not None:
        llm_is_spam = llm_result.get("is_spam", False)
        llm_score = llm_result.get("spam_score", 0.5)

        # 融合策略：ML 权重 55% + LLM 权重 45%（LLM 语义理解更强）
        combined_score = ml_score * 0.55 + llm_score * 0.45

        # 如果 ML 和 LLM 都认为是垃圾邮件，放大分数
        if ml_is_spam and llm_is_spam:
            combined_score = min(combined_score * 1.2, 1.0)
            final_is_spam = True
        # 如果只有一方认为是垃圾邮件，取加权平均
        elif ml_is_spam or llm_is_spam:
            final_is_spam = combined_score > 0.35
        else:
            final_is_spam = False

        detection_method = "ML+LLM"
        llm_reason = llm_result.get("reason", "")
    else:
        # LLM 不可用，纯 ML 判定
        combined_score = ml_score
        final_is_spam = ml_is_spam
        detection_method = "ML"
        llm_reason = ""

    # 4. 输出最终结果
    output = {
        "is_spam": final_is_spam,
        "spam_score": round(combined_score, 4),
        "confidence": round(ml_confidence, 4),
        "method": detection_method,
        "ml_is_spam": ml_is_spam,
        "ml_score": round(ml_score, 4),
        "result": ml_result.get("result", ""),
    }

    if llm_reason:
        output["llm_reason"] = llm_reason

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
