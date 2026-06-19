# -*- coding: utf-8 -*-
"""
优先级引擎评估脚本 — 用 training_set.json / test_set.json 验证评分准确率
"""

import os, sys, json, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("priority_eval")

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _PARENT)

from email_priority_plugin.priority_engine import PriorityEngine

# 数据集 label → 引擎内部 level 映射
LABEL_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "normal",
    "LOW": "low",
}

LEVEL_ORDER = {"critical": 3, "high": 2, "normal": 1, "low": 0}


def load_dataset(path: str) -> list:
    if not os.path.exists(path):
        logger.warning(f"数据集不存在: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"加载 {path}: {len(data)} 条样本")
    return data


def evaluate_engine(engine: PriorityEngine, dataset: list, name: str = "dataset"):
    exact_match = 0
    near_match = 0  # 相邻级别也算正确（如 HIGH→critical 或 HIGH→normal）
    total = len(dataset)
    details = []

    for item in dataset:
        email = {
            "from": item.get("sender", ""),
            "subject": item.get("subject", ""),
            "content": item.get("content", ""),
        }
        expected_label = item.get("priority", "MEDIUM")
        expected = LABEL_MAP.get(expected_label, "normal")

        result = engine.process(email)
        predicted = result.get("priority_level", "normal")

        exact = expected == predicted
        near = abs(LEVEL_ORDER.get(expected, 1) - LEVEL_ORDER.get(predicted, 1)) <= 1

        if exact:
            exact_match += 1
        if near:
            near_match += 1

        details.append({
            "subject": item.get("subject", "")[:45],
            "expected": expected,
            "predicted": predicted,
            "score": result.get("priority_score"),
            "exact": exact,
            "near": near,
        })

    exact_acc = exact_match / total if total > 0 else 0.0
    near_acc = near_match / total if total > 0 else 0.0
    return exact_acc, near_acc, exact_match, near_match, total, details


def print_report(exact_acc, near_acc, exact, near, total, details, name):
    print(f"\n{'='*60}")
    print(f"  {name} 评估结果")
    print(f"{'='*60}")
    print(f"  完全匹配: {exact_acc:.1%} ({exact}/{total})")
    print(f"  相邻容错: {near_acc:.1%} ({near}/{total})")
    print(f"{'='*60}")
    for d in details:
        s = "✓" if d["exact"] else ("~" if d["near"] else "✗")
        print(f"  {s} [{d['expected']:>8} → {d['predicted']:>8}] score={d['score']:.2f} | {d['subject']}")
    print(f"{'='*60}\n")


def main():
    # 初始化引擎（启用 LLM）
    engine = PriorityEngine()
    engine.init({
        "data_dir": os.path.join(_THIS_DIR, "data"),
        "user_stats_file": os.path.join(_THIS_DIR, "data", "user_behavior_stats.json"),
        "llm_api_key": "sk-isodwhtWqMq9DhZ7eSoiLEi2cnIeBmuaQq7hYHASTMifKTmh",
        "llm_provider": "custom",
        "llm_model": "deepseek-v4-pro",
        "llm_base_url": "https://www.micuapi.ai/v1",
    })

    # 训练集评估
    train = load_dataset(os.path.join(_THIS_DIR, "data", "training_set.json"))
    if train:
        ea, na, em, nm, tot, det = evaluate_engine(engine, train, "训练集 (training_set.json)")
        print_report(ea, na, em, nm, tot, det, "训练集")

    # 测试集评估
    test = load_dataset(os.path.join(_THIS_DIR, "data", "test_set.json"))
    if test:
        ea, na, em, nm, tot, det = evaluate_engine(engine, test, "测试集 (test_set.json)")
        print_report(ea, na, em, nm, tot, det, "测试集")

    engine.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())