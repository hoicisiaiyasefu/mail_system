# Email Priority Plugin (邮件优先级排序与预测性推送)

基于用户历史行为的邮件优先级排序引擎，实现 EmailPluginBase 接口，可插拔式集成。

## 功能特性

- **六维评分模型**：发件人互动频率 + 直接发送检测 + 紧急关键词 + 回复概率 + 时效性 + 大模型语义
- **用户行为学习**：基于打开率、回复频率、互动时间衰减持续优化评分
- **大模型可选**：用户可自行填写 API Key 启用 LLM 语义分析
- **异步处理**：支持后台排序，不阻塞邮件收发（`is_async = True`）
- **收件箱排序**：`sort_inbox()` 一次性排序整个收件箱
- **增量学习**：`record_user_action()` 持续学习用户偏好

## 目录结构

```
email_priority_plugin/
├── __init__.py
├── plugin_interface.py       # 插件统一接口基类
├── priority_engine.py        # 核心优先级引擎
├── user_behavior_model.py    # 用户行为统计模型
├── llm_api.py                # 大模型服务提供商接口
├── README.md
└── data/                     # 用户行为数据存储
```

## 快速开始

### 1. 基础使用（无 LLM）

```python
from email_priority_plugin import create_priority_engine

engine = create_priority_engine()
result = engine.process({
    "from": "boss@company.com",
    "to": "you@company.com",
    "subject": "紧急：项目截止日期提前",
    "content": "请尽快完成报告，due 明天",
})
print(result["priority_level"])  # 'critical'
```

### 2. 启用大模型分析

```python
engine = create_priority_engine(config={
    "llm_api_key": "sk-xxxxx",
    "llm_provider": "openai",  # 或 'custom' 用于兼容 API
    "llm_model": "gpt-3.5-turbo",
})
```

### 3. 收件箱排序

```python
sorted_inbox = engine.sort_inbox(emails, current_user="user@example.com")
for email in sorted_inbox:
    print(email["_priority_level"], email["subject"])
```

### 4. 记录用户行为（增量学习）

```python
engine.record_user_action("msg-001", "open", current_user="user@example.com")
engine.record_user_action("msg-001", "reply", current_user="user@example.com")
```

## 优先级级别

| 级别 | 分数范围 | 处理策略 |
|------|----------|----------|
| critical | 0.8 ~ 1.0 | 立即推送通知 |
| high | 0.6 ~ 0.8 | 置顶显示 |
| normal | 0.3 ~ 0.6 | 正常排序 |
| low | 0.0 ~ 0.3 | 折叠归档 |