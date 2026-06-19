# -*- coding: utf-8 -*-
"""
模型训练脚本 - 使用邮件数据集训练垃圾邮件检测模型
支持从现有 byes_mail_filter-main 项目的数据集加载训练数据
"""

import os
import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 将父目录加入路径以支持导入现有项目模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PARENT_DIR)

from spam_ml_plugin.ml_spam_detector import MLSpamDetector


def load_training_data_from_json(json_path: str):
    """
    从 JSON 文件加载训练数据
    JSON 格式: [{"content": "...", "label": 0/1, "is_spam": true/false}, ...]
    Args:
        json_path: JSON 文件路径
    Returns:
        tuple: (emails, labels) - 邮件文本列表和标签列表
    """
    import json

    if not os.path.exists(json_path):
        logger.warning(f"JSON 文件不存在: {json_path}")
        return [], []

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"读取 JSON 失败: {e}")
        return [], []

    emails = []
    labels = []

    for item in data:
        content = item.get("content", "") or ""
        subject = item.get("subject", "") or ""
        full_text = f"{subject} {content}".strip()
        if not full_text:
            continue

        label = item.get("label")
        if label is None:
            # 用 is_spam 兜底
            label = 1 if item.get("is_spam", False) else 0

        emails.append(full_text)
        labels.append(int(label))

    ham_count = labels.count(0)
    spam_count = labels.count(1)
    logger.info(f"从 JSON 加载: 正常邮件 {ham_count} 封, 垃圾邮件 {spam_count} 封, 总计 {len(emails)} 封")
    return emails, labels


def load_training_data_from_bayes_filter(data_dir: str):
    """
    从 byes_mail_filter-main 项目加载训练数据（保留作为备用方案）
    """
    import glob

    emails = []
    labels = []

    ham_dir = os.path.join(data_dir, "test-ham-1")
    if os.path.isdir(ham_dir):
        for filepath in glob.glob(os.path.join(ham_dir, "*")):
            if os.path.isfile(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if content.strip():
                        emails.append(content)
                        labels.append(0)
                except Exception as e:
                    logger.warning(f"读取正常邮件失败 {filepath}: {e}")

    logger.info(f"加载正常邮件: {len([l for l in labels if l == 0])} 封")

    spam_dir = os.path.join(data_dir, "test-spam-1")
    if os.path.isdir(spam_dir):
        for filepath in glob.glob(os.path.join(spam_dir, "*")):
            if os.path.isfile(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if content.strip():
                        emails.append(content)
                        labels.append(1)
                except Exception as e:
                    logger.warning(f"读取垃圾邮件失败 {filepath}: {e}")

    logger.info(f"加载垃圾邮件: {len([l for l in labels if l == 1])} 封")
    logger.info(f"总计: {len(emails)} 封邮件")

    return emails, labels


def generate_synthetic_data():
    """生成一些中英文混合的合成训练数据"""
    normal_emails = [
        "亲爱的同事，请查收附件中的项目进度报告。如有任何问题请随时联系我。祝好，张三",
        "Hi team, I have updated the project documentation on the shared drive. Please review and let me know your feedback. Best regards, Alice",
        "会议通知：项目组例会将于明天下午2点在会议室A举行，请准时参加。议题包括：1.进度汇报 2.资源分配 3.风险评估",
        "Hello, I wanted to follow up on the proposal we discussed last week. When would be a good time to meet? Thanks, Bob",
        "公司年度体检安排已出，请各位同事在5月30日前完成体检预约。如有特殊情况请联系HR。人事部",
        "Reminder: Team building activity this Friday at 4 PM. We'll meet at the main entrance. Don't forget to wear comfortable shoes!",
        "请各位同事注意，本周五下午3点将进行消防安全演练，届时请按照指示有序撤离。行政部",
        "I've reviewed your code changes and looks good overall. A few minor suggestions in the comments. Let's merge after fixing those. David",
    ]

    spam_emails = [
        "恭喜您中奖！您已获得百万大奖，请点击链接领取：http://fake-prize.example.com/claim 限时24小时！",
        "URGENT: Your account has been compromised! Click here immediately to verify your identity: http://192.168.1.100/phishing",
        "免费代办增值税发票，正规低价，咨询热线：138xxxx1234，专业代开各类票据，诚信合作！",
        "CONGRATULATIONS! You've won a free iPhone! Limited time offer, act now: http://win-free.tk/prize Click NOW!",
        "股票投资内部消息，稳赚不赔！加入VIP群获取每日涨停推荐。加微信：stock_master888",
        "Your PayPal account has been limited. Login to restore access: http://paypal-secure.ml/verify Please act urgently.",
        "代开咨询费、服务费发票，税点低，可验证后付款。联系电话：139xxxx5678 陈经理",
        "MAKE MONEY FAST! $5000 per week working from home! No experience needed! Visit http://easy-cash.ga/job NOW!!!",
    ]

    all_emails = normal_emails + spam_emails
    all_labels = [0] * len(normal_emails) + [1] * len(spam_emails)

    return all_emails, all_labels


def evaluate_model(detector: MLSpamDetector, emails: list, labels: list) -> dict:
    """评估模型性能"""
    correct = 0
    total = len(emails)
    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0

    for email, label in zip(emails, labels):
        result = detector.process({"content": email, "subject": ""})
        predicted = 1 if result["is_spam"] else 0

        if predicted == label:
            correct += 1

        if predicted == 1 and label == 1:
            true_positive += 1
        elif predicted == 1 and label == 0:
            false_positive += 1
        elif predicted == 0 and label == 0:
            true_negative += 1
        elif predicted == 0 and label == 1:
            false_negative += 1

    accuracy = correct / total if total > 0 else 0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "total": total,
        "correct": correct,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
    }


def main():
    parser = argparse.ArgumentParser(description="训练垃圾邮件检测 ML 模型")
    parser.add_argument(
        "--json-path",
        type=str,
        default=os.path.join(BASE_DIR, "data", "train_data.json"),
        help="JSON 训练数据文件路径（优先使用）",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="byes_mail_filter-main 项目目录（备用加载方式）",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=os.path.join(BASE_DIR, "models"),
        help="模型保存目录",
    )
    parser.add_argument(
        "--no-synthetic",
        action="store_true",
        default=False,
        help="禁用合成数据补充",
    )
    args = parser.parse_args()

    # 加载训练数据
    emails = []
    labels = []

    # 优先从 JSON 加载
    if os.path.exists(args.json_path):
        logger.info(f"从 JSON 加载训练数据: {args.json_path}")
        e, l = load_training_data_from_json(args.json_path)
        emails.extend(e)
        labels.extend(l)

    # 如无数据，尝试从贝叶斯项目加载
    if not emails and args.data_dir and os.path.isdir(args.data_dir):
        e, l = load_training_data_from_bayes_filter(args.data_dir)
        emails.extend(e)
        labels.extend(l)

    # 补充合成数据
    if not args.no_synthetic and (not emails or len(emails) < 20):
        e, l = generate_synthetic_data()
        emails.extend(e)
        labels.extend(l)

    if not emails:
        logger.error("没有可用的训练数据！")
        return 1

    logger.info(f"开始训练，共 {len(emails)} 封邮件...")

    # 创建并训练模型
    detector = MLSpamDetector()
    detector.init({"model_dir": args.model_dir})

    success = detector.train(emails, labels)
    if not success:
        logger.error("模型训练失败！")
        return 1

    # 评估模型
    logger.info("评估模型性能...")
    metrics = evaluate_model(detector, emails, labels)
    logger.info("模型评估结果：")
    logger.info(f"  准确率 (Accuracy):  {metrics['accuracy']:.2%}")
    logger.info(f"  精确率 (Precision): {metrics['precision']:.2%}")
    logger.info(f"  召回率 (Recall):    {metrics['recall']:.2%}")
    logger.info(f"  F1 分数 (F1-Score): {metrics['f1_score']:.2%}")
    logger.info(f"  总样本数: {metrics['total']}, 正确: {metrics['correct']}")
    logger.info(f"  TP: {metrics['true_positive']}, FP: {metrics['false_positive']}")
    logger.info(f"  TN: {metrics['true_negative']}, FN: {metrics['false_negative']}")

    detector.shutdown()
    logger.info(f"模型已保存至: {args.model_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())