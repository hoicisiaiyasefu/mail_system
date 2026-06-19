# -*- coding: utf-8 -*-
"""
插件统一接口基类
所有智能插件都应继承此基类，实现标准接口以便集成到邮件服务器中。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class EmailPluginBase(ABC):
    """邮件系统插件基类 - 所有插件必须实现此接口"""

    name: str = "base_plugin"
    version: str = "1.0.0"
    is_async: bool = False  # 是否支持异步处理

    @abstractmethod
    def init(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化插件
        Args:
            config: 配置字典，可包含 API Key、模型路径等
        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    def process(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理邮件数据（实时同步调用）
        Args:
            email_data: 邮件数据字典，包含：
                - 'id': 邮件ID
                - 'from': 发件人
                - 'to': 收件人
                - 'subject': 主题
                - 'content': 邮件正文
                - 'headers': 邮件头信息（可选）
                - 'attachments': 附件列表（可选）
        Returns:
            dict: 处理结果，包含：
                - 'plugin_name': 插件名称
                - 'result': 处理结果（具体格式由各插件定义）
                - 'confidence': 置信度（可选）
                - 'is_spam': 是否为垃圾邮件（垃圾邮件检测插件需要）
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        pass

    def process_async(self, email_data: Dict[str, Any], callback=None) -> None:
        """
        异步处理邮件数据（后台线程）
        子类可重写此方法实现异步处理逻辑
        Args:
            email_data: 邮件数据字典
            callback: 处理完成后的回调函数 callback(result)
        """
        import threading

        def _async_worker():
            result = self.process(email_data)
            if callback:
                callback(result)

        thread = threading.Thread(target=_async_worker, daemon=True)
        thread.start()

    def get_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": self.name,
            "version": self.version,
            "is_async": self.is_async,
        }