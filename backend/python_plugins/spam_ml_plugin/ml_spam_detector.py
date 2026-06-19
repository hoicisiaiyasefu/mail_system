# -*- coding: utf-8 -*-
"""
基于机器学习的垃圾邮件检测器
采用 TF-IDF 特征提取 + 朴素贝叶斯分类器的机器学习方案
支持通过 ctypes 加载 DLL（ONNX 推理引擎）作为升级方案
"""

import os
import re
import math
import pickle
import logging
import ctypes
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter
from pathlib import Path

from plugin_interface import EmailPluginBase

logger = logging.getLogger(__name__)

# ============================================================
# TF-IDF 特征提取器
# ============================================================

class TFIDFVectorizer:
    """TF-IDF 文本向量化器"""

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}  # 词 -> 索引
        self.idf: Dict[int, float] = {}        # 索引 -> IDF值
        self.doc_count = 0

    def fit(self, documents: List[str]) -> None:
        """
        在训练文档集上拟合 TF-IDF
        Args:
            documents: 文本列表
        """
        word_doc_count: Dict[str, int] = {}
        self.doc_count = len(documents)

        for doc in documents:
            words = set(self._tokenize(doc))
            for word in words:
                word_doc_count[word] = word_doc_count.get(word, 0) + 1

        # 构建词汇表
        idx = 0
        for word in sorted(word_doc_count.keys()):
            self.vocabulary[word] = idx
            # 计算 IDF: log(N / df)
            df = word_doc_count[word]
            self.idf[idx] = math.log((1 + self.doc_count) / (1 + df)) + 1
            idx += 1

    def transform(self, document: str) -> Dict[int, float]:
        """
        将单篇文档转为 TF-IDF 向量
        Args:
            document: 文本
        Returns:
            dict: {词汇索引: TF-IDF值}
        """
        tokens = self._tokenize(document)
        token_counts = Counter(tokens)
        total_tokens = len(tokens)

        if total_tokens == 0:
            return {}

        tfidf_vector: Dict[int, float] = {}
        for word, count in token_counts.items():
            if word in self.vocabulary:
                idx = self.vocabulary[word]
                tf = count / total_tokens
                tfidf_vector[idx] = tf * self.idf.get(idx, 1.0)

        return tfidf_vector

    def _tokenize(self, text: str) -> List[str]:
        """中文分词 + 英文分词简易实现"""
        import re

        # 清理 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 清理 URL
        text = re.sub(r'https?://\S+', ' URL ', text)
        # 清理邮件地址
        text = re.sub(r'\S+@\S+', ' EMAIL ', text)
        # 提取中英文单词
        # 中文：按字符切分
        # 英文：按空格和标点切分
        tokens = []
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        tokens.extend([w for w in english_words if len(w) > 1])

        # 提取中文字符（连续中文字符作为词）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for segment in chinese_chars:
            # 将中文段落按2-gram切分
            if len(segment) <= 2:
                tokens.append(segment)
            else:
                for i in range(len(segment) - 1):
                    tokens.append(segment[i:i+2])

        return tokens


# ============================================================
# 朴素贝叶斯分类器
# ============================================================

class MultinomialNaiveBayes:
    """多项朴素贝叶斯分类器"""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha  # 拉普拉斯平滑
        self.class_log_prior: Dict[int, float] = {}
        self.feature_log_prob: Dict[int, Dict[int, float]] = {}
        self.classes: List[int] = [0, 1]  # 0: 正常, 1: 垃圾

    def fit(self, X: List[Dict[int, float]], y: List[int]) -> None:
        """
        训练分类器
        Args:
            X: TF-IDF 特征向量列表
            y: 标签列表 (0=正常, 1=垃圾)
        """
        n_samples = len(X)
        class_counts = Counter(y)

        # 特征总数（词汇表大小）
        n_features = 0
        for vec in X:
            if vec:
                n_features = max(n_features, max(vec.keys()) + 1)

        # 计算先验概率（对数空间）
        for cls in self.classes:
            self.class_log_prior[cls] = math.log(class_counts.get(cls, 0) / n_samples)

        # 计算每个类别的特征条件概率
        for cls in self.classes:
            # 类别 cls 下所有特征值之和
            feat_sum: Dict[int, float] = {}
            total_sum = 0.0

            for vec, label in zip(X, y):
                if label == cls:
                    for idx, value in vec.items():
                        feat_sum[idx] = feat_sum.get(idx, 0.0) + value
                        total_sum += value

            # 拉普拉斯平滑后的对数概率
            self.feature_log_prob[cls] = {}
            for idx in range(n_features):
                feat_count = feat_sum.get(idx, 0.0)
                self.feature_log_prob[cls][idx] = math.log(
                    (feat_count + self.alpha) / (total_sum + self.alpha * n_features)
                ) if (total_sum + self.alpha * n_features) > 0 else 0.0

    def predict_proba(self, X: Dict[int, float]) -> Dict[int, float]:
        """
        预测概率分布
        Args:
            X: TF-IDF 特征向量
        Returns:
            dict: {类别: 概率}
        """
        log_probs: Dict[int, float] = {}

        for cls in self.classes:
            log_prob = self.class_log_prior.get(cls, math.log(0.5))
            for idx, value in X.items():
                log_prob += value * self.feature_log_prob.get(cls, {}).get(idx, 0.0)
            log_probs[cls] = log_prob

        # 对数概率转概率（使用 softmax）
        max_log = max(log_probs.values())
        exp_probs = {cls: math.exp(lp - max_log) for cls, lp in log_probs.items()}
        total = sum(exp_probs.values())

        if total == 0:
            return {cls: 1.0 / len(self.classes) for cls in self.classes}

        return {cls: p / total for cls, p in exp_probs.items()}

    def predict(self, X: Dict[int, float]) -> int:
        """预测类别"""
        proba = self.predict_proba(X)
        best_cls = self.classes[0]
        best_prob = proba.get(best_cls, 0.0)
        for cls in self.classes:
            if proba.get(cls, 0.0) > best_prob:
                best_prob = proba[cls]
                best_cls = cls
        return best_cls


# ============================================================
# DLL 动态链接库加载器 (ONNX 推理引擎)
# ============================================================

class DLLInferenceEngine:
    """
    通过 ctypes 加载 C++ DLL 进行 ONNX 模型推理
    如果 DLL 加载失败，自动回退到 Python 纯实现
    """

    def __init__(self, dll_path: Optional[str] = None):
        self.dll = None
        self.dll_loaded = False
        self.dll_path = dll_path or self._find_dll()

    def _find_dll(self) -> str:
        """自动查找 DLL 文件"""
        search_paths = [
            os.path.join(os.path.dirname(__file__), "spam_ml_core", "build", "Release", "spam_inference.dll"),
            os.path.join(os.path.dirname(__file__), "spam_ml_core", "build", "spam_inference.dll"),
            os.path.join(os.path.dirname(__file__), "spam_inference.dll"),
        ]
        for path in search_paths:
            if os.path.exists(path):
                return path
        return search_paths[0]

    def load(self) -> bool:
        """尝试加载 DLL"""
        try:
            if os.path.exists(self.dll_path):
                # 抑制 ctypes.CDLL 在失败时向 stderr 打印的错误信息
                # 使用 os.dup2 底层重定向（比 sys.stderr 重定向更彻底）
                old_fd = os.dup(2)
                null_fd = os.open(os.devnull, os.O_WRONLY)
                os.dup2(null_fd, 2)
                try:
                    self.dll = ctypes.CDLL(self.dll_path)
                finally:
                    os.dup2(old_fd, 2)
                    os.close(null_fd)
                    os.close(old_fd)
                # 设置函数签名
                self.dll.predict_spam.argtypes = [ctypes.c_char_p]
                self.dll.predict_spam.restype = ctypes.c_double
                self.dll.init_model.argtypes = [ctypes.c_char_p]
                self.dll.init_model.restype = ctypes.c_bool
                self.dll_loaded = True
                return True
            else:
                return False
        except Exception:
            return False

    def init_model(self, model_path: str) -> bool:
        """初始化 ONNX 模型"""
        if self.dll_loaded and self.dll:
            try:
                return self.dll.init_model(model_path.encode('utf-8'))
            except Exception:
                return False
        return False

    def predict(self, text: str) -> float:
        """
        预测邮件为垃圾邮件的概率
        Returns:
            float: 0.0 ~ 1.0 之间的概率值
        """
        if self.dll_loaded and self.dll:
            try:
                return self.dll.predict_spam(text.encode('utf-8'))
            except Exception:
                pass
        return -1.0  # 表示 DLL 推理失败，需要回退


# ============================================================
# 垃圾邮件检测规则引擎（辅助）
# ============================================================

class RuleEngine:
    """基于规则的垃圾邮件辅助检测（增强版）"""

    # 垃圾邮件特征关键词（大幅扩充中文关键词）
    SPAM_KEYWORDS = [
        # 赚钱/兼职/理财诈骗
        '免费', '优惠', '促销', '中奖', '领奖', '赚钱', '日赚', '高薪', '兼职',
        '投资', '理财', '股票', '开户', '贷款', '涨停', '牛股', '年收益',
        '稳赚不赔', '内部消息', '名额有限', '限时', '错过', '抢购',
        '秒杀', '最低价', '特价', '清仓', '包邮',
        # 代办/发票/证件
        '代办', '代开', '发票', '增值税', '证件', '办证', '刻章',
        '出售', '购买', '购买', '转让', '回收', '高价', '低价',
        # 博彩/色情
        '博彩', '赌博', '赌场', '彩票', '下注', '赔率',
        'viagra', 'casino', 'lottery', 'winner', 'prize', 'betting',
        # 紧急/欺诈
        'urgent', 'act now', 'limited time', 'click here', 'click',
        'congratulations', 'you won', 'free money',
        '异常登录', '账号锁定', '身份验证', '冻结', '安全验证',
        '系统检测', '异地登录', '风险',
        # 其他垃圾特征
        '微信号', '微信', 'QQ', '加群', '入群', '刷单', '打字员',
        '包过', '代写论文', '代考', '替考',
        '包下卡', '无前期', '信用卡', '储蓄卡',
    ]

    # 垃圾邮件 URL 特征
    SUSPICIOUS_URL_PATTERNS = [
        r'https?://\d+\.\d+\.\d+\.\d+',  # IP 地址 URL
        r'https?://.*\.(tk|ml|ga|cf|gq)\b',  # 免费域名
        r'https?://.*\.(xyz|top|win|vip)\b',  # 廉价域名
    ]

    # 教育/机构/高校 URL 白名单（不会被当作可疑 URL）
    ACADEMIC_URL_WHITELIST = [
        '.edu', '.edu.cn', '.ac.cn', '.ac.uk', '.gov.cn',
        'cqvip.com', 'cnki.net', 'wanfangdata.com',  # 学术论文平台
        'scut.edu', 'scut',  # 华南理工大学
    ]

    # 垃圾邮件特征正则（额外检测模式）
    SPAM_PATTERNS = [
        (r'\d{11}', 'phone_number', 0.15),              # 手机号
        (r'\d{3,4}[-]?\d{7,8}', 'landline', 0.10),      # 座机
        (r'日[赚挣]\d+', 'daily_earn', 0.25),            # 日赚XX
        (r'[¥￥]\d+', 'money_amount', 0.10),             # 金额
        (r'\d+元', 'rmb_amount', 0.10),                   # XX元
        (r'微信[：:]?\w+', 'wechat_id', 0.20),           # 微信号
        (r'QQ[：:]?\d+', 'qq_id', 0.15),                  # QQ号
        (r'点击.*链接', 'click_link', 0.15),              # 点击链接
        (r'http[s]?://', 'any_url', 0.15),                # 任意URL
        (r'限.*小时内', 'time_pressure', 0.20),           # 限时压力
        (r'[1-9]\d{4,}', 'long_number', 0.10),            # 长数字
        (r'加.*微信', 'add_wechat', 0.20),                # 加微信
        (r'[A-Z]{8,}', 'long_uppercase', 0.15),           # 长串大写
        # 乱码/随机文本检测
        (r'^[a-z0-9]{10,}$', 'alphanumeric_only', 0.35), # 纯字母数字无空格（乱码特征）
        (r'[a-z]{15,}', 'long_lowercase', 0.25),          # 长串小写字母（无意义）
    ]

    # 键盘乱打特征（QWERTY键盘连续按键）
    KEYBOARD_MASH_PATTERNS = [
        'qwerty', 'asdfgh', 'zxcvbn', 'qazwsx', 'wsxedc',
        'rfvtgb', 'yhnmju', 'asdfghjkl', 'qwertyuiop',
        '123456', '12345', 'abcdef', 'aaaaa', 'bbbbb',
        'xcvbnm', 'sdfghj', 'dfghjk', 'fghjkl', 'ghjkl;',
        'edcft', 'ikmju', 'ujmik', 'olp', 'plok',
    ]

    @classmethod
    def extract_features(cls, email_content: str) -> Dict[str, float]:
        """
        从邮件内容提取规则特征（增强版）
        Returns:
            dict: 特征字典
        """
        content_lower = email_content.lower()
        features = {}

        # 关键词命中计数（直接用命中数而非占比）
        hit_count = 0
        for keyword in cls.SPAM_KEYWORDS:
            if keyword.lower() in content_lower:
                hit_count += 1
        features['keyword_hit_count'] = float(hit_count)
        features['keyword_total'] = float(len(cls.SPAM_KEYWORDS))
        features['keyword_hit_ratio'] = hit_count / max(len(cls.SPAM_KEYWORDS), 1)

        # 模式匹配得分
        pattern_score = 0.0
        for pattern, _, weight in cls.SPAM_PATTERNS:
            matches = re.findall(pattern, content_lower)
            if matches:
                pattern_score += min(len(matches) * weight, 0.5)
        features['pattern_score'] = min(pattern_score, 1.0)

        # URL 数量（排除教育/机构白名单域名）
        urls = re.findall(r'https?://\S+', content_lower)
        whitelisted_urls = 0
        for url in urls:
            for domain in cls.ACADEMIC_URL_WHITELIST:
                if domain.lower() in url.lower():
                    whitelisted_urls += 1
                    break
        features['url_count'] = len(urls) - whitelisted_urls  # 扣掉白名单URL
        features['whitelisted_url_count'] = whitelisted_urls

        # 可疑 URL 数量
        suspicious_urls = 0
        for pattern in cls.SUSPICIOUS_URL_PATTERNS:
            found_urls = re.findall(pattern, content_lower)
            for url in found_urls:
                is_whitelisted = False
                for domain in cls.ACADEMIC_URL_WHITELIST:
                    if domain.lower() in url.lower():
                        is_whitelisted = True
                        break
                if not is_whitelisted:
                    suspicious_urls += 1
        features['suspicious_url_count'] = suspicious_urls

        # 全大写单词占比
        upper_words = re.findall(r'\b[A-Z]{3,}\b', email_content)
        total_words = len(re.findall(r'\b\w+\b', email_content))
        features['all_caps_ratio'] = len(upper_words) / max(total_words, 1)

        # 感叹号占比
        exclamation = email_content.count('!')
        features['exclamation_ratio'] = exclamation / max(len(email_content), 1)

        # 邮件长度（短邮件可能是垃圾邮件）
        features['content_length'] = len(email_content)

        # ============================================================
        # 乱码/随机文本检测（新增）
        # ============================================================
        # 是否有空格/换行（正常邮件通常有）
        has_whitespace = bool(re.search(r'\s', email_content))
        features['has_whitespace'] = 1.0 if has_whitespace else 0.0

        # 中文/英文有效词汇占比
        chinese_chars = len(re.findall(r'[一-鿿]', email_content))
        english_words = len(re.findall(r'\b[a-z]{2,}\b', content_lower))
        total_chars = max(len(email_content), 1)
        features['chinese_ratio'] = chinese_chars / total_chars
        features['english_word_count'] = float(english_words)

        # 键盘乱打检测
        mash_hits = 0
        for pattern in cls.KEYBOARD_MASH_PATTERNS:
            if pattern in content_lower:
                mash_hits += 1
        features['keyboard_mash_hits'] = float(mash_hits)

        # 乱码综合评分：无空格 + 无有效词汇 + 纯字母数字
        gibberish_score = 0.0
        # 注意：中文文本天然没有空格，不能因此扣分
        if not has_whitespace and total_chars > 8 and chinese_chars == 0:
            # 无空白字符的长文本（非中文）→ 可疑
            gibberish_score += 0.30
        if chinese_chars == 0 and english_words == 0 and total_chars > 8:
            # 没有任何有效词汇 → 很可疑
            gibberish_score += 0.40
        elif chinese_chars == 0 and english_words <= 2 and total_chars > 15 and mash_hits >= 2:
            # 少量"英文词"但其实是键盘乱打 → 可疑
            gibberish_score += 0.35
        if mash_hits >= 3:
            # 大量键盘乱打 → 极其可疑（几乎可以确定是垃圾/无意义内容）
            gibberish_score = 0.80  # 直接覆盖为高分，不管其他条件
        elif mash_hits >= 1:
            gibberish_score += 0.25
        if total_chars > 5 and total_chars < 200 and chinese_chars == 0 and english_words <= 1 and not has_whitespace:
            # 短乱码文本（5-200字符，无词汇，无空格）→ 高度可疑
            gibberish_score += 0.30
        features['gibberish_score'] = min(gibberish_score, 1.0)

        return features


# ============================================================
# ML 垃圾邮件检测器主类
# ============================================================

class MLSpamDetector(EmailPluginBase):
    """
    基于机器学习的垃圾邮件检测器
    实现 EmailPluginBase 接口，可作为插件加载到邮件服务器
    """

    name = "ml_spam_detector"
    version = "1.0.0"
    is_async = False  # 垃圾邮件检测需要实时处理

    def __init__(self):
        super().__init__()
        self.vectorizer: Optional[TFIDFVectorizer] = None
        self.classifier: Optional[MultinomialNaiveBayes] = None
        self.rule_engine = RuleEngine()
        self.dll_engine = DLLInferenceEngine()
        self.is_trained = False
        self.model_dir: str = ""
        self._model_loaded = False

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化检测器
        Args:
            config: 配置字典，可选：
                - 'model_dir': 模型存储目录
                - 'dll_path': DLL 路径
                - 'auto_train': 是否使用默认数据自动训练
        """
        try:
            config = config or {}
            self.model_dir = config.get(
                'model_dir',
                os.path.join(os.path.dirname(__file__), 'models')
            )
            os.makedirs(self.model_dir, exist_ok=True)

            # 尝试加载 DLL
            dll_path = config.get('dll_path')
            if dll_path:
                self.dll_engine = DLLInferenceEngine(dll_path)
            dll_loaded = self.dll_engine.load()

            # 尝试加载预训练模型
            if not dll_loaded:
                vectorizer_path = os.path.join(self.model_dir, 'vectorizer.pkl')
                classifier_path = os.path.join(self.model_dir, 'classifier.pkl')

                if os.path.exists(vectorizer_path) and os.path.exists(classifier_path):
                    self._load_model(vectorizer_path, classifier_path)
                    self._model_loaded = True
                    logger.info("预训练 ML 模型加载成功")
            else:
                # DLL 模式：加载 ONNX 模型
                onnx_path = os.path.join(self.model_dir, 'spam_model.onnx')
                if os.path.exists(onnx_path):
                    self.dll_engine.init_model(onnx_path)
                    self._model_loaded = True
                    logger.info("ONNX 模型通过 DLL 加载成功")

            self.is_trained = self._model_loaded
            logger.info(f"ML垃圾邮件检测器初始化完成，模型状态: {'已加载' if self._model_loaded else '未训练'}")
            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False

    def process(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        实时处理邮件，检测是否为垃圾邮件
        Args:
            email_data: 邮件数据，至少包含 'content' 字段
        Returns:
            dict: {
                'plugin_name': 'ml_spam_detector',
                'is_spam': bool,
                'confidence': float (0~1),
                'spam_score': float (0~1),
                'rule_features': dict,
                'result': str (人类可读的结果描述),
            }
        """
        content = email_data.get('content', '')
        subject = email_data.get('subject', '')
        full_text = f"{subject} {subject} {content}"  # 主题加权

        # 规则引擎特征
        rule_features = self.rule_engine.extract_features(full_text)

        # 对纯正文再做一次乱码检测（防止主题中的正常词汇掩盖正文乱码）
        content_features = self.rule_engine.extract_features(content)
        content_gibberish = content_features.get('gibberish_score', 0)
        full_gibberish = rule_features.get('gibberish_score', 0)
        # 取正文和全文的乱码评分最大值
        rule_features['gibberish_score'] = max(full_gibberish, content_gibberish)

        # 规则引擎评分
        rule_spam_score = self._rule_based_score(rule_features)

        # ML 模型评分（如果已训练）
        ml_spam_score = 0.5
        ml_confidence = 0.0

        if self.is_trained and self.vectorizer and self.classifier:
            try:
                features = self.vectorizer.transform(full_text)
                proba = self.classifier.predict_proba(features)
                ml_spam_score = proba.get(1, 0.5)
                ml_confidence = abs(ml_spam_score - 0.5) * 2  # 转换到0~1
            except Exception as e:
                logger.error(f"ML 预测失败: {e}")
                ml_spam_score = 0.5
                ml_confidence = 0.0

        # 尝试 DLL 推理
        if self.dll_engine.dll_loaded:
            dll_score = self.dll_engine.predict(full_text)
            if dll_score >= 0:
                ml_spam_score = dll_score
                ml_confidence = abs(ml_spam_score - 0.5) * 2

        # 综合评分：ML 60% + 规则 40%
        if ml_confidence > 0:
            combined_score = ml_spam_score * 0.6 + rule_spam_score * 0.4
            confidence = ml_confidence * 0.6 + (1.0 if rule_spam_score > 0.7 else 0.3) * 0.4
        else:
            combined_score = rule_spam_score
            confidence = 0.5

        # 阈值调整为 0.50（0.30 过于激进，大量误判正常邮件为垃圾）
        is_spam = combined_score > 0.50

        # 生成人类可读的结果描述
        if combined_score > 0.80:
            result = "高度疑似垃圾邮件"
        elif combined_score > 0.65:
            result = "可能为垃圾邮件"
        elif combined_score > 0.50:
            result = "可能为正常邮件"
        else:
            result = "正常邮件"

        return {
            'plugin_name': self.name,
            'is_spam': is_spam,
            'confidence': round(confidence, 4),
            'spam_score': round(combined_score, 4),
            'rule_features': rule_features,
            'result': result,
        }

    def _rule_based_score(self, features: Dict[str, float]) -> float:
        """基于规则特征计算垃圾邮件分数（增强版：用命中数而非占比）"""
        score = 0.0
        weights = 0.0

        # 关键词命中数（不是占比，直接按命中数评分）
        hit_count = features.get('keyword_hit_count', 0)
        if hit_count >= 5:
            score += 1.0  # 5个以上关键词 → 满分
        elif hit_count >= 3:
            score += 0.85
        elif hit_count >= 2:
            score += 0.65
        elif hit_count >= 1:
            score += 0.40
        else:
            score += 0.0
        weights += 1.0

        # 模式得分（手机号、微信号等）
        pattern_score = features.get('pattern_score', 0)
        score += pattern_score * 0.8
        weights += 0.8

        # 可疑 URL 数量
        suspicious = features.get('suspicious_url_count', 0)
        score += min(suspicious, 3) * 0.25
        weights += 0.25

        # URL 总数
        url_count = features.get('url_count', 0)
        score += min(url_count / 5, 1.0) * 0.15
        weights += 0.15

        # 全大写单词占比
        score += min(features.get('all_caps_ratio', 0) * 3, 1.0) * 0.10
        weights += 0.10

        # 叹号占比
        score += min(features.get('exclamation_ratio', 0) * 20, 1.0) * 0.10
        weights += 0.10

        # 乱码/随机文本评分（高权重：乱码是强垃圾信号）
        gibberish = features.get('gibberish_score', 0)
        if gibberish >= 0.5:
            # 中高乱码 → 直接返回高分，不与其他低分特征平均
            return 0.65 + (gibberish - 0.5) * 0.7  # 0.5→0.65, 0.7→0.79, 1.0→1.0
        score += gibberish * 1.5
        weights += 1.5

        # 内容长度异常（极短乱码 → 更强信号）
        content_len = features.get('content_length', 0)
        if content_len > 0 and features.get('gibberish_score', 0) > 0.5 and content_len < 100:
            score += 0.30
            weights += 0.30

        return score / max(weights, 1.0)

    def train(self, emails: List[str], labels: List[int]) -> bool:
        """
        使用训练数据训练模型
        Args:
            emails: 邮件文本列表
            labels: 标签列表 (0=正常, 1=垃圾)
        Returns:
            bool: 训练是否成功
        """
        try:
            self.vectorizer = TFIDFVectorizer()
            self.vectorizer.fit(emails)

            X = [self.vectorizer.transform(email) for email in emails]

            self.classifier = MultinomialNaiveBayes(alpha=1.0)
            self.classifier.fit(X, labels)

            self.is_trained = True
            self._model_loaded = True

            # 保存模型
            self._save_model()
            logger.info(f"模型训练完成，样本数: {len(emails)}")
            return True

        except Exception as e:
            logger.error(f"训练失败: {e}")
            return False

    def _save_model(self) -> None:
        """保存模型到磁盘"""
        if self.vectorizer and self.classifier:
            vectorizer_path = os.path.join(self.model_dir, 'vectorizer.pkl')
            classifier_path = os.path.join(self.model_dir, 'classifier.pkl')
            with open(vectorizer_path, 'wb') as f:
                pickle.dump(self.vectorizer, f)
            with open(classifier_path, 'wb') as f:
                pickle.dump(self.classifier, f)
            logger.info(f"模型已保存到 {self.model_dir}")

    def _load_model(self, vectorizer_path: str, classifier_path: str) -> None:
        """从磁盘加载模型"""
        with open(vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)
        with open(classifier_path, 'rb') as f:
            self.classifier = pickle.load(f)
        self.is_trained = True

    def shutdown(self) -> None:
        """关闭插件"""
        if self.dll_engine and self.dll_engine.dll_loaded:
            try:
                if self.dll_engine.dll and hasattr(ctypes, 'windll'):
                    # 释放 DLL（仅 Windows）
                    ctypes.windll.kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]
                    # DLL 会在进程退出时自动释放
            except Exception:
                pass


# ============================================================
# 暴露给外部使用的便捷函数
# ============================================================

def create_detector(config: Optional[Dict[str, Any]] = None) -> MLSpamDetector:
    """工厂函数：创建并初始化检测器"""
    detector = MLSpamDetector()
    detector.init(config)
    return detector