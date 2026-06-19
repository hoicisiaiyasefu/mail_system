# -*- coding: utf-8 -*-
"""
垃圾邮件检测评估脚本 — 用 test_data.json 独立评估模型准确率
"""

import os, sys, json, logging, argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("spam_eval")

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _PARENT)

from spam_ml_plugin.ml_spam_detector import MLSpamDetector


def load_dataset(path: str):
    if not os.path.exists(path):
        logger.warning(f"测试集不存在: {path}")
        return [], []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    emails, labels = [], []
    for item in data:
        content = item.get("content", "") or ""
        subject = item.get("subject", "") or ""
        full_text = f"{subject} {content}".strip()
        if not full_text:
            continue
        label = item.get("label")
        if label is None:
            label = 1 if item.get("is_spam", False) else 0
        emails.append(full_text)
        labels.append(int(label))

    logger.info(f"加载 {path}: 正常 {labels.count(0)}, 垃圾 {labels.count(1)}, 总计 {len(emails)}")
    return emails, labels


def evaluate(detector: MLSpamDetector, emails: list, labels: list):
    correct = 0
    tp = fp = tn = fn = 0
    total = len(emails)
    details = []

    for email, label in zip(emails, labels):
        result = detector.process({"content": email, "subject": ""})
        predicted = 1 if result.get("is_spam") else 0

        if predicted == label:
            correct += 1
        if predicted == 1 and label == 1:
            tp += 1
        elif predicted == 1 and label == 0:
            fp += 1
        elif predicted == 0 and label == 0:
            tn += 1
        elif predicted == 0 and label == 1:
            fn += 1

        details.append({
            "text_preview": email[:50],
            "expected": "spam" if label else "ham",
            "predicted": "spam" if predicted else "ham",
            "score": result.get("spam_score", 0),
            "correct": predicted == label,
        })

    acc = correct / total if total > 0 else 0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0

    return {
        "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "total": total, "correct": correct,
        "details": details,
    }


def print_report(metrics: dict, name: str):
    print(f"\n{'='*60}")
    print(f"  {name} 评估结果")
    print(f"{'='*60}")
    print(f"  准确率 : {metrics['accuracy']:.1%}")
    print(f"  精确率 : {metrics['precision']:.1%}")
    print(f"  召回率 : {metrics['recall']:.1%}")
    print(f"  F1     : {metrics['f1']:.1%}")
    print(f"  TP={metrics['tp']}  FP={metrics['fp']}  TN={metrics['tn']}  FN={metrics['fn']}")
    print(f"{'='*60}")
    for d in metrics.get("details", []):
        s = "✓" if d["correct"] else "✗"
        print(f"  {s} [{d['expected']:>4} → {d['predicted']:>4}] score={d['score']:.2f} | {d['text_preview']}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="评估垃圾邮件检测模型")
    parser.add_argument("--json-path", default=os.path.join(_THIS_DIR, "data", "test_data.json"))
    parser.add_argument("--model-dir", default=os.path.join(_THIS_DIR, "models"))
    args = parser.parse_args()

    emails, labels = load_dataset(args.json_path)
    if not emails:
        logger.error("无评估数据")
        return 1

    detector = MLSpamDetector()
    detector.init({"model_dir": args.model_dir})

    # 初始化后若未加载到预训练模型，则用 train_data.json 训练
    if not detector.is_trained:
        logger.info("未找到已训练模型，先用 train_data.json 训练...")
        train_path = os.path.join(_THIS_DIR, "data", "train_data.json")
        if os.path.exists(train_path):
            from model_train import load_training_data_from_json
            train_e, train_l = load_training_data_from_json(train_path)
            if train_e:
                detector.train(train_e, train_l)
            else:
                logger.error("训练数据为空")
                return 1
        else:
            logger.error(f"训练数据不存在: {train_path}")
            return 1

    metrics = evaluate(detector, emails, labels)
    print_report(metrics, "测试集 (test_data.json)")

    detector.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())