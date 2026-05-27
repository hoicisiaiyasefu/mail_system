# -*- coding: utf-8 -*-
"""
安全引擎评估脚本 — 用 training_set.json / test_set.json 验证检测准确率
"""

import os, sys, json, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("security_eval")

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _PARENT)

from plugin_interface import EmailPluginBase
from security_ai_plugin.security_engine import SecurityEngine

RISK_ORDER = {"safe": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def load_dataset(path: str) -> list:
    if not os.path.exists(path):
        logger.warning(f"数据集不存在: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"加载 {path}: {len(data)} 条样本")
    return data


def map_risk_to_label(risk_level: str) -> str:
    """将引擎输出的 risk_level 映射到数据集中的 risk_level 标签"""
    return risk_level


def evaluate_engine(engine: SecurityEngine, dataset: list, name: str = "dataset"):
    correct_level = 0
    total = len(dataset)
    details = []

    for item in dataset:
        email = {
            "from": item.get("sender", ""),
            "subject": item.get("subject", ""),
            "content": item.get("content", ""),
            "links": item.get("links", []),
        }
        expected = item.get("risk_level", "safe")
        result = engine.process(email)
        predicted = map_risk_to_label(result.get("risk_level", "safe"))

        # 视为"正确"：安全/低风险 vs 中/高/严重至少同向
        is_dangerous_expected = expected in ("high", "critical", "medium")
        is_dangerous_predicted = predicted in ("high", "critical", "medium")
        level_correct = is_dangerous_expected == is_dangerous_predicted

        if level_correct:
            correct_level += 1

        details.append({
            "subject": item.get("subject", "")[:40],
            "expected": expected,
            "predicted": predicted,
            "score": result.get("risk_score"),
            "threats_found": len(result.get("threats", [])),
            "correct": level_correct,
        })

    accuracy = correct_level / total if total > 0 else 0.0
    return accuracy, correct_level, total, details


def print_report(accuracy, correct, total, details, name):
    print(f"\n{'='*60}")
    print(f"  {name} 评估结果")
    print(f"{'='*60}")
    print(f"  准确率: {accuracy:.1%} ({correct}/{total})")
    print(f"{'='*60}")
    for d in details:
        status = "✓" if d["correct"] else "✗"
        print(f"  {status} [{d['expected']:>8} → {d['predicted']:>8}] score={d['score']:.2f} | {d['subject']}")
    print(f"{'='*60}\n")


def main():
    # 初始化引擎（启用 LLM 深度分析）
    engine = SecurityEngine()
    engine.init({
        "enable_link_expand": False,
        "llm_api_key": "sk-isodwhtWqMq9DhZ7eSoiLEi2cnIeBmuaQq7hYHASTMifKTmh",
        "llm_provider": "custom",
        "llm_model": "deepseek-v4-pro",
        "llm_base_url": "https://www.micuapi.ai/v1",
    })

    # 训练集评估
    train = load_dataset(os.path.join(_THIS_DIR, "data", "training_set.json"))
    if train:
        acc, corr, tot, det = evaluate_engine(engine, train, "训练集 (training_set.json)")
        print_report(acc, corr, tot, det, "训练集")

    # 测试集评估
    test = load_dataset(os.path.join(_THIS_DIR, "data", "test_set.json"))
    if test:
        acc, corr, tot, det = evaluate_engine(engine, test, "测试集 (test_set.json)")
        print_report(acc, corr, tot, det, "测试集")

    engine.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())