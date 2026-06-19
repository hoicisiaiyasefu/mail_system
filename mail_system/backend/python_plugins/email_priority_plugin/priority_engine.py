# -*- coding: utf-8 -*-
"""
邮件优先级排序引擎
基于用户历史行为（打开率、回复频率、发件人重要性等）预测邮件重要性
支持实时评分 + 异步学习更新
"""

import os
import json
import pickle
import sys
import logging
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

from plugin_interface import EmailPluginBase
from .user_behavior_model import UserBehaviorModel
from .llm_api import LLMServiceProvider

# 尝试导入公共 LLM provider（PluginRegistry 注入）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
try:
    from llm_sdk_provider import BaseLLMProvider  # noqa: F401
except ImportError:
    BaseLLMProvider = None  # type: ignore

logger = logging.getLogger(__name__)


class PriorityEngine(EmailPluginBase):
    """
    邮件优先级排序引擎
    实现 EmailPluginBase 接口，可作为插件加载到邮件服务器

    特征维度：
    - 发件人历史互动频率
    - 收件人是否在收件人列表中（直接发送 vs 群发）
    - 邮件是否包含紧急关键词
    - 用户对类似邮件的打开率
    - 时间衰减：近期互动更有价值
    - 大模型语义分析（可选，需 API Key）
    """

    name = "email_priority_engine"
    version = "1.0.0"
    is_async = True  # 优先级排序可以异步运行，不阻塞收发

    # 优先级阈值范围（降低阈值以提升 critical/high 识别率）
    PRIORITY_CRITICAL = (0.55, 1.0)   # 紧急：需要立即处理
    PRIORITY_HIGH = (0.40, 0.55)      # 重要：置顶显示
    PRIORITY_NORMAL = (0.20, 0.40)    # 普通：正常排序
    PRIORITY_LOW = (0.0, 0.20)        # 低优先级：折叠或归档

    # 紧急关键词库
    URGENT_KEYWORDS = {
        'zh': ['紧急', '尽快', '截止', '务必', '立即', '加急',
               '告警', '故障', '异常', '安全', '漏洞', '数据泄露'],
        'en': ['urgent', 'asap', 'deadline', 'critical', 'alert',
               'security', 'breach', 'incident', 'emergency',
               'action required', 'immediate', 'important'],
    }

    def __init__(self):
        super().__init__()
        self.behavior_model: Optional[UserBehaviorModel] = None
        self.llm_service: Optional[LLMServiceProvider] = None
        self.data_dir: str = ""
        self.llm_enabled: bool = False
        self._initialized: bool = False

        # 运行时缓存：当前用户的互动统计
        self._user_stats: Dict[str, Dict[str, Any]] = {}

    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化优先级引擎
        Args:
            config: {
                'data_dir': str,           # 数据存储目录
                'user_stats_file': str,    # 用户行为统计文件
                'llm_api_key': str,        # 大模型 API Key（可选）
                'llm_provider': str,       # 大模型提供商: 'openai' / 'local'
                'llm_model': str,          # 模型名称
                'llm_base_url': str,       # API 基础 URL
            }
        """
        try:
            config = config or {}
            self.data_dir = config.get(
                'data_dir',
                os.path.join(os.path.dirname(__file__), 'data')
            )
            os.makedirs(self.data_dir, exist_ok=True)

            # 初始化用户行为模型
            self.behavior_model = UserBehaviorModel()
            stats_file = config.get(
                'user_stats_file',
                os.path.join(self.data_dir, 'user_behavior_stats.json')
            )
            if os.path.exists(stats_file):
                self.behavior_model.load(stats_file)
            else:
                # 使用默认初始数据
                self.behavior_model.initialize_defaults()
                self.behavior_model.save(stats_file)

            # 加载用户统计到缓存
            self._load_user_stats()

            # 可选 LLM — 优先使用 PluginRegistry 注入的共享 provider
            shared_llm = config.get('_llm_provider')
            if shared_llm is not None and BaseLLMProvider is not None and isinstance(shared_llm, BaseLLMProvider):
                self.llm_service = LLMServiceProvider(_shared_provider=shared_llm)
                self.llm_enabled = shared_llm.test_connection()
            else:
                llm_api_key = config.get('llm_api_key')
                if llm_api_key:
                    self.llm_service = LLMServiceProvider(
                        api_key=llm_api_key,
                        provider=config.get('llm_provider', 'openai'),
                        model=config.get('llm_model', 'gpt-3.5-turbo'),
                        base_url=config.get('llm_base_url'),
                    )
                    self.llm_enabled = self.llm_service.test_connection()
                logger.info(f"大模型服务状态: {'已连接' if self.llm_enabled else '连接失败'}")

            self._initialized = True
            logger.info(f"邮件优先级引擎初始化完成, LLM: {'已启用' if self.llm_enabled else '未启用'}")
            return True

        except Exception as e:
            logger.error(f"优先级引擎初始化失败: {e}")
            return False

    def process(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算单封邮件的优先级分数
        Args:
            email_data: 邮件数据
        Returns:
            dict: {
                'plugin_name': str,
                'priority_score': float,     # 0.0~1.0
                'priority_level': str,       # 'critical'/'high'/'normal'/'low'
                'features': dict,            # 各特征得分明细
                'suggestion': str,           # 处理建议
                'should_push': bool,         # 是否应该推送通知
            }
        """
        from_email = email_data.get('from', '')
        subject = email_data.get('subject', '')
        content = email_data.get('content', '')
        to_field = email_data.get('to', '')
        current_user = email_data.get('current_user', 'default')

        features = {}

        # 1. 发件人互动频率得分 (权重 0.20)
        sender_score = self._calculate_sender_score(from_email, current_user)
        features['sender_engagement'] = sender_score

        # 2. 直接发送 vs 群发得分 (权重 0.10)
        direct_score = self._calculate_direct_score(to_field, current_user)
        features['is_direct_message'] = direct_score

        # 3. 紧急关键词得分 (权重 0.30)
        urgency_score = self._calculate_urgency_score(subject, content)
        features['urgency_keywords'] = urgency_score

        # 4. 历史回复概率 (权重 0.15)
        reply_score = self._calculate_reply_probability(from_email, subject, current_user)
        features['reply_probability'] = reply_score

        # 5. 时效性得分 (权重 0.15)
        time_score = self._calculate_timeliness_score(email_data)
        features['timeliness'] = time_score

        # 6. 大模型语义分析 (权重 0.10, 可选)
        llm_score = 0.5
        if self.llm_enabled and self.llm_service:
            llm_score = self._calculate_llm_score(subject, content, from_email)
        features['llm_analysis'] = llm_score

        # 加权综合得分（提升紧急关键词和大模型权重）
        priority_score = (
            sender_score * 0.20 +
            direct_score * 0.10 +
            urgency_score * 0.30 +
            reply_score * 0.15 +
            time_score * 0.15 +
            llm_score * 0.10
        )

        # 确定优先级级别
        priority_level = self._get_priority_level(priority_score)
        should_push = priority_score >= 0.40  # 降低推送阈值

        # 生成处理建议
        suggestion = self._generate_suggestion(priority_level, features)

        return {
            'plugin_name': self.name,
            'priority_score': round(priority_score, 4),
            'priority_level': priority_level,
            'features': features,
            'suggestion': suggestion,
            'should_push': should_push,
        }

    def process_async(self, email_data: Dict[str, Any], callback=None) -> None:
        """
        异步处理（推荐用于批量排序场景）
        此方法已在基类中实现，这里显式暴露以支持后台排序
        """
        super().process_async(email_data, callback)

    def sort_inbox(self, emails: List[Dict[str, Any]],
                   current_user: str = 'default') -> List[Dict[str, Any]]:
        """
        对收件箱邮件列表进行排序
        Args:
            emails: 邮件列表
            current_user: 当前用户标识
        Returns:
            list: 按优先级降序排列的邮件列表
        """
        for email in emails:
            email['current_user'] = current_user
            result = self.process(email)
            email['_priority_score'] = result['priority_score']
            email['_priority_level'] = result['priority_level']
            email['_should_push'] = result['should_push']

        return sorted(emails, key=lambda x: x.get('_priority_score', 0), reverse=True)

    def record_user_action(self, email_id: str, action: str,
                            current_user: str = 'default') -> None:
        """
        记录用户对邮件的操作，用于持续学习
        Args:
            email_id: 邮件ID
            action: 操作类型 ('open', 'reply', 'delete', 'ignore', 'archive')
            current_user: 用户标识
        """
        self.behavior_model.update(email_id, action, current_user)

        # 定期保存到磁盘
        stats_file = os.path.join(self.data_dir, 'user_behavior_stats.json')
        self.behavior_model.save(stats_file)

    # ============================================================
    # 私有方法：各维度评分计算
    # ============================================================

    def _calculate_sender_score(self, from_email: str,
                                 current_user: str) -> float:
        """
        发件人互动频率得分
        基于：历史打开率、回复频率、最近互动时间
        """
        if not from_email:
            return 0.3  # 未知发件人给中性分

        sender_stats = self.behavior_model.get_sender_stats(
            from_email, current_user
        )

        if not sender_stats:
            return 0.3  # 首次通信，中性分数

        open_rate = sender_stats.get('open_rate', 0.0)
        reply_rate = sender_stats.get('reply_rate', 0.0)
        last_interaction_days = sender_stats.get('last_interaction_days', 30)

        # 时效性衰减：越近的互动越重要
        time_factor = max(0.1, 1.0 - last_interaction_days / 60.0)

        # 综合评分
        score = (open_rate * 0.4 + reply_rate * 0.4 + time_factor * 0.2)

        return max(0.0, min(1.0, score))

    def _calculate_direct_score(self, to_field: str,
                                 current_user: str) -> float:
        """
        判断邮件是否直接发送给当前用户
        直接发送 = 1.0，群发 = 0.3，广播 = 0.1
        """
        if not to_field:
            return 0.5

        recipients = [r.strip().lower() for r in to_field.split(',')]

        if len(recipients) == 1:
            return 1.0  # 直接发送

        if current_user.lower() in recipients:
            if len(recipients) <= 5:
                return 0.7  # 小群组
            else:
                return 0.4  # 大群发

        return 0.2  # 未在收件人列表中

    def _calculate_urgency_score(self, subject: str, content: str) -> float:
        """
        紧急关键词匹配得分（增强版：区分高/低紧急度关键词）
        """
        text = f"{subject} {subject} {content}"  # 主题加权
        text_lower = text.lower()

        # 高紧急度关键词（命中即大幅加分）
        HIGH_URGENCY_KEYWORDS = [
            '紧急', '尽快', '截止', '务必', '立即', '加急',
            '告警', '故障', '异常', '安全', '漏洞', '数据泄露',
            'urgent', 'asap', 'deadline', 'critical', 'alert',
            'security', 'breach', 'incident', 'emergency',
            'action required', 'immediate', 'important',
        ]

        # 中紧急度关键词
        MEDIUM_URGENCY_KEYWORDS = [
            '请注意', '提醒', '通知', '更新', '变更',
            '注意', 'attention', 'reminder', 'update', 'notice',
        ]

        high_hits = 0
        medium_hits = 0

        for kw in HIGH_URGENCY_KEYWORDS:
            if kw.lower() in text_lower:
                count = text_lower.count(kw.lower())
                high_hits += min(count, 3)  # 每个词最多计3次

        for kw in MEDIUM_URGENCY_KEYWORDS:
            if kw.lower() in text_lower:
                count = text_lower.count(kw.lower())
                medium_hits += min(count, 2)

        # 分段评分：高紧急度关键词权重远大于中等
        if high_hits >= 3:
            score = 0.85 + min(high_hits - 3, 3) * 0.05  # 0.85~1.0
        elif high_hits >= 2:
            score = 0.65 + (high_hits - 2) * 0.10  # 0.65~0.75
        elif high_hits >= 1:
            score = 0.40 + medium_hits * 0.10  # 0.40~0.60
        elif medium_hits >= 2:
            score = 0.25 + min(medium_hits - 2, 2) * 0.05  # 0.25~0.35
        elif medium_hits >= 1:
            score = 0.15
        else:
            score = 0.10  # 无任何关键词命中

        return min(1.0, score)

    def _calculate_reply_probability(self, from_email: str,
                                       subject: str,
                                       current_user: str) -> float:
        """
        预测用户回复概率
        基于发件人历史回复率和主题相似度
        """
        if not from_email:
            return 0.3

        sender_stats = self.behavior_model.get_sender_stats(
            from_email, current_user
        )

        if not sender_stats:
            return 0.3

        reply_rate = sender_stats.get('reply_rate', 0.0)
        interaction_count = sender_stats.get('interaction_count', 0)

        # 互动次数越多，回复率越可信
        confidence = min(interaction_count / 20.0, 1.0)

        # 融合置信度和回复率
        score = reply_rate * confidence + 0.3 * (1 - confidence)

        return max(0.0, min(1.0, score))

    def _calculate_timeliness_score(self, email_data: Dict[str, Any]) -> float:
        """
        时效性得分：根据邮件中提到的日期/时间判断紧迫性
        """
        content = email_data.get('content', '')
        subject = email_data.get('subject', '')
        text = f"{subject} {content}"

        import re

        score = 0.5  # 默认中性

        # 检测"今天"、"明天"等近期时间词
        today_keywords = ['今天', '今日', 'today', 'tonight']
        tomorrow_keywords = ['明天', '明日', 'tomorrow']
        soon_keywords = ['尽快', '24小时', '24小时', 'within 24',
                         'asap', 'immediately', '今天下午', '今早']

        for kw in today_keywords:
            if kw.lower() in text.lower():
                score = 0.8
                break

        for kw in tomorrow_keywords:
            if kw.lower() in text.lower() and score < 0.7:
                score = 0.7

        for kw in soon_keywords:
            if kw.lower() in text.lower() and score < 0.9:
                score = 0.9

        # 如果有明确的过期日期检测
        deadline_match = re.findall(
            r'(截止|deadline|due)[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}月\d{1,2}日)',
            text.lower()
        )
        if deadline_match:
            score = max(score, 0.85)

        return score

    def _calculate_llm_score(self, subject: str, content: str,
                              from_email: str) -> float:
        """
        使用大模型进行语义重要性分析
        """
        if not self.llm_service:
            return 0.5

        try:
            prompt = (
                f"分析以下邮件的紧急程度，返回0到1之间的分数。"
                f"考虑因素：是否有截止日期、是否需要回复、是否涉及安全问题、"
                f"发件人语气是否紧迫。\n\n"
                f"发件人: {from_email}\n"
                f"主题: {subject}\n"
                f"内容: {content[:500]}\n\n"
                f"请仅返回一个0到1之间的浮点数。"
            )

            result = self.llm_service.chat(prompt, "请仅返回一个0到1之间的浮点数，不要包含其他内容。")
            # 尝试从结果中提取数字
            import re
            numbers = re.findall(r'0\.\d+|\d+\.\d+', result)
            if numbers:
                score = float(numbers[0])
                return max(0.0, min(1.0, score))
        except Exception as e:
            logger.warning(f"LLM 分析失败: {e}")

        return 0.5

    def _get_priority_level(self, score: float) -> str:
        """将分数映射为优先级级别"""
        if score >= self.PRIORITY_CRITICAL[0]:
            return 'critical'
        elif score >= self.PRIORITY_HIGH[0]:
            return 'high'
        elif score >= self.PRIORITY_NORMAL[0]:
            return 'normal'
        else:
            return 'low'

    def _generate_suggestion(self, level: str,
                               features: Dict[str, float]) -> str:
        """生成处理建议"""
        suggestions = {
            'critical': '建议立即处理，推送实时通知',
            'high': '建议置顶显示，优先查看',
            'normal': '正常排序，常规处理',
            'low': '可归档或稍后处理',
        }

        # 根据特征微调建议
        base = suggestions.get(level, '正常处理')
        if features.get('urgency_keywords', 0) > 0.7:
            base += '；检测到紧急关键词'
        if features.get('sender_engagement', 0) > 0.8:
            base += '；来自高频对话联系人'
        if features.get('is_direct_message', 0) > 0.9:
            base += '；直接发送给您'

        return base

    def _load_user_stats(self) -> None:
        """从行为模型加载用户统计到内存缓存"""
        if self.behavior_model:
            self._user_stats = self.behavior_model.get_all_stats()

    def shutdown(self) -> None:
        """关闭引擎，保存状态"""
        if self.behavior_model:
            stats_file = os.path.join(self.data_dir, 'user_behavior_stats.json')
            self.behavior_model.save(stats_file)
        if self.llm_service:
            self.llm_service.close()
        self._initialized = False
        logger.info("邮件优先级引擎已关闭")


# ============================================================
# 便捷函数
# ============================================================

def create_priority_engine(config: Optional[Dict[str, Any]] = None) -> PriorityEngine:
    """工厂函数：创建并初始化优先级引擎"""
    engine = PriorityEngine()
    engine.init(config)
    return engine