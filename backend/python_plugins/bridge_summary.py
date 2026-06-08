#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件摘要生成桥接脚本
通过命令行参数接收 JSON 邮件数据，使用 LLM 生成邮件摘要

用法:
  python bridge_summary.py '<json_email_data>'                               # 无配置（截断降级）
  python bridge_summary.py '<json_email_data>' '<json_config>'               # 有配置（LLM 生成）
"""

import sys
import json
import os
import re

# ============================================================
# 彻底抑制 stderr
# ============================================================
_devnull_fd = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull_fd, 2)
os.close(_devnull_fd)

# 确保能找到同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugin_registry import init_registry


def _text_quality_score(text: str) -> float:
    """
    评估文本质量分数 (0~1)
    分值越高表示文本越像正常的人类书写内容
    """
    if not text or len(text) < 3:
        return 0.0

    score = 0.0
    total = len(text)

    # 1. 有空格/换行（正常文本特征）+0.25
    if re.search(r'\s', text):
        score += 0.25

    # 2. 有中文或英文词典词汇 +0.30
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    english_words = len(re.findall(r'\b[a-z]{2,}\b', text.lower()))
    if chinese_chars > 2 or english_words >= 2:
        score += 0.30
    elif chinese_chars > 0 or english_words > 0:
        score += 0.10

    # 3. 有标点符号（句号、逗号等）+0.20
    punctuation = len(re.findall(r'[。，！？、；：,\.!\?;:\-]', text))
    if punctuation >= 2:
        score += 0.20
    elif punctuation >= 1:
        score += 0.10

    # 4. 长度适中（30-5000字符）+0.15
    if 30 <= total <= 5000:
        score += 0.15
    elif total >= 15:
        score += 0.05

    # 5. 键盘乱打检测 — 大量乱打直接判为无意义
    mash_patterns = ['qwerty', 'asdfgh', 'zxcvbn', 'qazwsx', 'abcdef',
                     '12345', 'aaaa', 'bbbb', 'cccc', 'dddd',
                     'sdfghj', 'dfghjk', 'fghjkl', 'xcvbnm',
                     'asdfghjkl', 'qwertyuiop']
    mash_count = 0
    for mp in mash_patterns:
        if mp in text.lower():
            mash_count += 1
    if mash_count >= 2:
        return 0.0  # 大量键盘乱打，直接返回质量0
    elif mash_count >= 1:
        score -= 0.40

    # 6. 纯字母数字无空格 + 无词汇 → 扣分
    if re.match(r'^[a-z0-9]+$', text.lower()) and chinese_chars == 0 and english_words == 0:
        score -= 0.35

    return max(0.0, min(1.0, score))


def extractive_summary(text: str, max_length: int = 120) -> str:
    """
    提取式摘要（LLM 不可用时的降级方案）
    从原文中提取关键句子作为摘要
    """
    if not text:
        return ""

    # 清理 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    if not text:
        return "（空内容，无法生成摘要）"

    # 乱码检测：如果文本质量太低，直接返回提示
    quality = _text_quality_score(text)
    if quality < 0.15:
        return "（内容疑似乱码或无意义文本，无法生成有效摘要）"

    if len(text) <= max_length:
        return text

    # 按句子分割
    sentences = re.split(r'[。！？\n;；]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if not sentences:
        return text[:max_length] + "..."

    # 优先选择包含关键信息的句子
    important_keywords = [
        '通知', '会议', '截止', '重要', '紧急', '请', '需要', '确认',
        '时间', '地点', '安排', '汇总', '报告', '问题',
        'meeting', 'deadline', 'important', 'urgent', 'please', 'confirm',
    ]

    scored_sentences = []
    for sent in sentences:
        score = 1.0
        sent_lower = sent.lower()
        for kw in important_keywords:
            if kw.lower() in sent_lower:
                score += 1.5
        # 首句加分
        if sentences.index(sent) == 0:
            score += 1.0
        scored_sentences.append((sent, score))

    # 按分数降序排列，取前几句
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    summary = ""
    for sent, _ in scored_sentences:
        if len(summary) + len(sent) + 1 <= max_length:
            summary += sent + "。"
        else:
            break

    if not summary:
        summary = sentences[0][:max_length] + "..."

    return summary.strip()


def llm_generate_summary(llm, email_data: dict, max_length: int = 120):
    """
    使用大模型生成邮件摘要
    返回: dict 或 None
    """
    if llm is None or not llm.is_connected:
        return None

    subject = email_data.get('subject', '')
    content = email_data.get('content', '')
    from_addr = email_data.get('from', '')

    prompt = (
        f"请为以下邮件生成一段简洁的中文摘要（不超过{max_length}字），"
        f"概括发件人意图和关键信息：\n\n"
        f"发件人：{from_addr}\n"
        f"主题：{subject}\n"
        f"正文：{content[:2000]}\n\n"
        f"请直接输出摘要内容，不要包含引号或其他修饰。"
    )

    try:
        summary = llm.chat(
            messages=[
                {"role": "system", "content": "你是一个专业的邮件助手，擅长提炼邮件要点。请简洁、准确地总结邮件内容。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_length * 3,
            temperature=0.2,
        )
        summary = summary.strip().strip('"').strip("'").strip()
        if summary:
            return summary
        return None
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "缺少邮件数据参数"}))
        sys.exit(1)

    try:
        email_data = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON 解析失败(邮件数据): {str(e)}"}))
        sys.exit(1)

    # 摘要长度配置（可从邮件数据中指定）
    max_length = int(email_data.get('summary_max_length', 120))

    # 可选的配置文件/JSON 参数
    config_dict = None
    if len(sys.argv) >= 3:
        try:
            config_dict = json.loads(sys.argv[2])
        except (json.JSONDecodeError, Exception):
            pass

    try:
        registry = init_registry(config_dict=config_dict)
    except Exception as e:
        print(json.dumps({"error": f"插件注册表初始化失败: {str(e)}"}))
        sys.exit(1)

    # 1. 尝试 LLM 生成摘要
    llm = registry.get_llm()
    llm_summary = llm_generate_summary(llm, email_data, max_length)

    if llm_summary:
        # LLM 生成成功
        print(json.dumps({
            "summary": llm_summary,
            "method": "llm",
            "length": len(llm_summary),
        }, ensure_ascii=False))
    else:
        # 2. 降级：提取式摘要
        subject = email_data.get('subject', '')
        content = email_data.get('content', '')
        full_text = f"{subject}。{content}"

        # 单独检查正文质量（防止正常主题掩盖乱码正文）
        content_quality = _text_quality_score(content) if content else 1.0
        if content_quality < 0.15 and subject:
            # 正文是乱码但有正常主题 → 摘要只反映主题，标记正文异常
            extractive = f"主题：{subject}（正文内容无法解析，疑似无意义内容）"
        else:
            extractive = extractive_summary(full_text, max_length)
        print(json.dumps({
            "summary": extractive,
            "method": "extractive",
            "length": len(extractive),
            "fallback": True if llm is not None and llm.is_connected else False,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
