# Python 智能插件系统

邮件系统的 Python 端插件层，提供垃圾邮件检测、安全威胁分析和邮件优先级排序三大智能能力。

---

## 目录结构

```
python_plugins/
├── plugin_interface.py              # 统一插件接口规范 (AbstractPlugin)
├── plugin_registry.py               # 插件注册中心（单例，管理 LLM 共享 + 生命周期）
├── llm_sdk_provider.py              # 大模型 SDK 抽象层（OpenAI SDK / HTTP 兼容）
│
├── bridge_spam.py                   # 桥接脚本：垃圾邮件检测
├── bridge_security.py               # 桥接脚本：安全威胁分析
├── bridge_priority.py               # 桥接脚本：邮件优先级排序
│
├── spam_ml_plugin/                  # 插件1：ML 垃圾邮件检测
│   ├── ml_spam_detector.py          #   主引擎（ONNX 推理 + Python 回退）
│   ├── model_train.py               #   模型训练脚本
│   ├── spam_ml_core/                #   C++ ONNX 推理核心
│   └── data/                        #   训练/测试数据
│
├── security_ai_plugin/              # 插件2：AI 安全威胁分析
│   ├── security_engine.py           #   主引擎（规则 + LLM 增强）
│   ├── spoof_detector.py            #   发件人伪造检测
│   ├── threat_detector.py           #   威胁类型识别
│   ├── link_analyzer.py             #   恶意链接分析
│   ├── llm_api.py                   #   LLM 调用封装
│   └── data/                        #   测试数据
│
└── email_priority_plugin/           # 插件3：邮件优先级排序
    ├── priority_engine.py           #   主引擎（规则 + 用户模型 + LLM 增强）
    ├── user_behavior_model.py       #   用户行为统计模型
    ├── llm_api.py                   #   LLM 调用封装
    └── data/                        #   用户行为统计数据
```

---

## 一、三个插件引擎

### 1. spam_ml_plugin — ML 垃圾邮件检测

**文件**: `spam_ml_plugin/ml_spam_detector.py`
**类名**: `MLSpamDetector`

基于机器学习的垃圾邮件检测器，优先使用 C++ ONNX 推理（高性能），无 DLL 时自动降级为 Python 回退方案。

| 输入字段 | 类型 | 说明 |
|---------|------|------|
| `subject` | str | 邮件主题 |
| `content` | str | 邮件正文 |
| `from` | str | 发件人地址 |

| 输出字段 | 类型 | 说明 |
|---------|------|------|
| `is_spam` | bool | 是否垃圾邮件 |
| `spam_score` | float (0~1) | 垃圾邮件置信度 |
| `result` | str | 详细判定说明 |

---

### 2. security_ai_plugin — AI 安全威胁分析

**文件**: `security_ai_plugin/security_engine.py`
**类名**: `SecurityEngine`

多维度邮件安全分析引擎，涵盖伪造检测、钓鱼链接、恶意意图识别。

| 输入字段 | 类型 | 说明 |
|---------|------|------|
| `from` | str | 发件人地址 |
| `subject` | str | 邮件主题 |
| `content` | str | 邮件正文（含链接） |
| `headers` | dict (可选) | 邮件原始头部 |
| `attachments` | list (可选) | 附件信息 |

| 输出字段 | 类型 | 说明 |
|---------|------|------|
| `risk_level` | str | safe / low / medium / high / critical |
| `risk_score` | float (0~1) | 综合风险评分 |
| `is_spoofed` | bool | 是否伪造发件人 |
| `threats` | list | 威胁列表 `[{type, detail}]` |
| `malicious_links` | list | 恶意链接 `[{url, reason}]` |
| `recommendation` | str | 处理建议 |

**子模块**：
- `spoof_detector.py`：基于规则的发件人伪造检测（域名相似度、知名品牌冒充）
- `threat_detector.py`：威胁类型识别（钓鱼关键词、紧急话术、可疑模式）
- `link_analyzer.py`：恶意链接分析（IP 地址链接、短链接、可疑 TLD）

---

### 3. email_priority_plugin — 邮件优先级排序

**文件**: `email_priority_plugin/priority_engine.py`
**类名**: `PriorityEngine`

综合用户行为模型和邮件内容特征的优先级评分引擎。

| 输入字段 | 类型 | 说明 |
|---------|------|------|
| `from` | str | 发件人地址 |
| `subject` | str | 邮件主题 |
| `content` | str | 邮件正文 |
| `current_user` | str | 当前用户标识 |

| 输出字段 | 类型 | 说明 |
|---------|------|------|
| `priority_score` | float (0~1) | 优先级评分 |
| `priority_level` | str | critical / high / normal / low |
| `suggestion` | str | 处理建议 |

**子模块**：
- `user_behavior_model.py`：用户行为统计（常联系人频率、回复率、阅读时间等），数据持久化到 `data/user_behavior_stats.json`

---

## 二、公共模块

### plugin_interface.py — 统一插件接口

```python
class AbstractPlugin(ABC):
    def init(self, config: dict) -> bool:    # 初始化（接收配置 + LLM provider）
    def process(self, email: dict) -> dict:   # 处理邮件，返回结果
    def shutdown(self) -> None:               # 释放资源
```

所有插件引擎都遵循此接口，确保 `PluginRegistry` 可以统一管理。

### plugin_registry.py — 插件注册中心

**类**: `PluginRegistry`（单例模式）

核心职责：
1. **LLM 实例统一创建与共享** — 只创建一次 LLM 连接，注入到所有插件
2. **插件发现与注册** — 从配置中读取插件列表，动态加载
3. **统一 process 入口** — `registry.process(plugin_name, email_data)`
4. **批量处理** — `registry.process_all(email_data)` 一次调用所有插件

**便捷函数**：
```python
from plugin_registry import init_registry
registry = init_registry(config_dict={...})  # 一键初始化
```

### llm_sdk_provider.py — LLM SDK 抽象层

**类层次**：`BaseLLMProvider` → `OpenAIProvider` / `HttpLLMProvider`

| provider 值 | 实现方式 | 依赖 |
|------------|---------|------|
| `openai` | OpenAI Python SDK | `pip install openai` |
| `custom` | 纯 HTTP 请求（urllib） | 无额外依赖 |

支持的 API 兼容服务：OpenAI、vLLM、Ollama、LM Studio 等。

**工厂函数**：
```python
from llm_sdk_provider import create_llm_provider
provider = create_llm_provider(api_key="sk-xxx", provider="openai", model="gpt-3.5-turbo")
```

---

## 三、桥接脚本（Bridge Scripts）

三个桥接脚本是 Java 后端与 Python 插件之间的桥梁，通过命令行参数传递 JSON 数据。

### bridge_spam.py

```bash
python3 bridge_spam.py '<json_email_data>' '<json_config>'
```

| 参数 | 说明 |
|------|------|
| `json_email_data` | 邮件 JSON 字符串 `{"from":"...", "subject":"...", "content":"..."}` |
| `json_config` | 可选，插件配置 JSON（含 LLM 配置和插件开关） |

输出：垃圾邮件检测结果 JSON（stdout 单行）

### bridge_security.py

```bash
python3 bridge_security.py '<json_email_data>' '<json_config>'
```

输出：安全分析结果 JSON

### bridge_priority.py

```bash
python3 bridge_priority.py '<json_email_data>' '<json_config>'
```

输出：优先级评分结果 JSON

---

## 四、使用方式

### 方式1：独立 Python 调用（命令行测试）

```bash
cd mail_system/backend
python3 python_plugins/bridge_spam.py '{"from":"spam@test.com","subject":"中奖通知","content":"恭喜您..."}'
```

### 方式2：Pipeline 批处理

```bash
# 从项目根目录运行
cd /home/lyq/实训
python3 test_pipeline.py              # 用模拟邮件测试
python3 mail_pipeline.py --limit 10   # 拉取 QQ 邮箱分析（需配置 POP3）
```

### 方式3：在 Python 代码中直接使用

```python
import sys
sys.path.insert(0, 'mail_system/backend/python_plugins')

from plugin_registry import init_registry

registry = init_registry(config_dict={
    'llm': {'enabled': False},
    'plugins': {
        'spam_ml_plugin': {'enabled': True},
        'security_ai_plugin': {'enabled': True},
        'email_priority_plugin': {'enabled': True},
    }
})

results = registry.process_all({
    'from': 'boss@company.com',
    'subject': '会议通知',
    'content': '周五下午2点开会...',
})

print(results['spam_ml_plugin']['is_spam'])       # False
print(results['security_ai_plugin']['risk_level'])  # safe
print(results['email_priority_plugin']['priority_level'])  # high

registry.shutdown()
```

---

## 五、LLM 大模型配置指南

### 配置位置

配置通过 `application.yml` 或 `plugins_config.json` 传入：

```yaml
# application.yml
llm:
  enabled: true                # 启用大模型
  api-key: "sk-xxxxxxxx"       # API 密钥
  provider: openai             # openai | custom
  model: gpt-3.5-turbo         # 模型名称
  base-url: ""                 # 自定义 API 地址，留空用默认
```

或 JSON 格式：
```json
{
  "llm": {
    "enabled": true,
    "api_key": "sk-xxxxxxxx",
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "base_url": ""
  }
}
```

### 支持的 LLM 服务

| 服务 | provider 值 | base_url 示例 | 说明 |
|------|------------|--------------|------|
| OpenAI 官方 | `openai` | 留空 | 需要 `pip install openai` |
| 自定义兼容 API | `custom` | `https://your-api.com/v1` | 无额外依赖，纯 HTTP |
| Ollama 本地 | `custom` | `http://localhost:11434/v1` | 免费本地运行 |
| vLLM | `custom` | `http://localhost:8000/v1` | 自部署高性能推理 |

### 降级策略

当 LLM 未启用或连接失败时，所有插件自动降级为**纯规则模式**：
- **安全引擎**：基于关键词、域名特征、URL 模式进行规则检测
- **优先级引擎**：使用本地用户行为模型 + 内容特征评分
- **垃圾邮件检测**：使用本地 ML 模型（不依赖 LLM）

> **设计原则**：用户自行决定是否填写 API Key。未配置时不影响基础邮件功能。

---

## 六、邮件输入 JSON 规范

所有插件接收统一的邮件 JSON 格式：

```json
{
  "id": 12345,
  "from": "sender@example.com",
  "to": "receiver@example.com",
  "subject": "邮件主题",
  "content": "邮件正文内容...",
  "date": "Mon, 26 May 2026 10:00:00 +0800",
  "headers": {
    "Return-Path": "...",
    "Received": "...",
    "DKIM-Signature": "..."
  },
  "attachments": [
    {"filename": "report.pdf", "size": 102400, "mime_type": "application/pdf"}
  ],
  "current_user": "user@qq.com"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `from` | ✅ | 发件人地址 |
| `subject` | ✅ | 邮件主题 |
| `content` | ✅ | 邮件正文 |
| `to` | - | 收件人地址 |
| `date` | - | 发送时间 |
| `headers` | - | 原始邮件头（安全检测用） |
| `attachments` | - | 附件列表 |
| `current_user` | - | 当前用户标识（优先级引擎用） |