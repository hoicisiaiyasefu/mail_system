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

---

## 七、Java 后端集成方式

### 调用链路

```
MailController.receiveMail()
  → MailService.receiveMail()         // 保存邮件到数据库，立即返回
  → SpamAsyncService.detectAndUpdate() // @Async 异步，不阻塞响应
    → SpamDetectorService.detect()     // 构建 JSON 参数
      → PythonBridge.execute()         // 启动子进程：python3 bridge_spam.py
        → PluginRegistry.process()     // Python 端加载插件并推理
      ← JSON 结果 Map<String,Object>
    ← 解析 is_spam / spam_score
  ← 回写数据库：Mail.is_spam, Mail.spam_score, Mail.folder
```

### 关键类说明

| 类 | 文件位置 | 职责 |
|----|---------|------|
| `PythonBridge` | `ai/PythonBridge.java` | 通用 Python 桥接器，通过 `ProcessBuilder` 调用任意 bridge 脚本，自动适配 Windows/Linux 的 `python`/`python3` 命令 |
| `SpamDetectorService` | `ai/SpamDetectorService.java` | 封装 `bridge_spam.py` 调用，构建邮件 JSON 参数 |
| `SpamAsyncService` | `service/SpamAsyncService.java` | `@Async` 异步执行，解析结果并回写数据库 `is_spam`/`spam_score`/`folder` |
| `MailController` | `controller/MailController.java` | REST 接口层，`POST /api/mail/receive` 接收邮件后自动触发检测 |

### 异步机制

- 邮件保存后接口**立即返回**（status=RECEIVED），不等待 AI 检测
- 后台 `@Async` 线程调用 Python，通常 1~3 秒内完成
- 检测完成后自动更新数据库字段：`is_spam` (0/1), `spam_score` (0~1), `folder` (SPAM/INBOX)
- 前端轮询 `GET /api/mail/{id}` 即可获取最新垃圾邮件标签

### 配置文件

Spring Boot 配置在 `backend/src/main/resources/application.yml`：

```yaml
plugin:
  python-path: python3            # Python 命令（Windows 自动切换为 python）
  plugins-dir: python_plugins     # 插件目录
  config-file: python_plugins/plugins_config.json

llm:
  enabled: true                   # 是否启用大模型
  api-key: "your-api-key"         # LLM API 密钥
  provider: openai
  model: gpt-3.5-turbo
  base-url: ""                    # 自定义 API 地址

plugins:
  spam_ml_plugin:
    enabled: true                 # 启用垃圾邮件检测
  security_ai_plugin:
    enabled: true                 # 启用安全分析
  email_priority_plugin:
    enabled: true                 # 启用优先级排序
```

> **安全提醒**：`application.yml` 和 `plugins_config.json` 包含 API Key，**不要提交到 Git**。 参见下方"十、启动流程"中的 template 配置方式。

---

## 八、测试方法

### 8.1 REST API 测试

启动后端（`mvn spring-boot:run`）后，使用 curl 进行端到端测试。

**发一封正常邮件**：
```bash
curl -s -X POST http://localhost:8080/api/mail/receive \
  -H "Content-Type: application/json" \
  -d '{
    "from": "colleague@company.com",
    "to": "user@example.com",
    "subject": "项目周会通知",
    "content": "各位同事好，本周三下午3点将在会议室A召开项目周会，请大家提前准备各自的工作进展汇报。"
  }' | python3 -m json.tool
```

**发一封垃圾邮件**：
```bash
curl -s -X POST http://localhost:8080/api/mail/receive \
  -H "Content-Type: application/json" \
  -d '{
    "from": "spammer@scam.com",
    "to": "user@example.com",
    "subject": "恭喜您中了500万大奖",
    "content": "尊敬的客户您好！恭喜您在本次抽奖活动中获得了500万元现金大奖！请点击链接填写个人信息领取奖金。限时优惠免费包邮，错过今天再等一年！"
  }' | python3 -m json.tool
```

**查询结果（等待2-3秒后）**：
```bash
# 替换 {id} 为实际邮件ID
curl -s http://localhost:8080/api/mail/{id} | python3 -m json.tool
```

预期输出：
```json
{
    "id": 5,
    "from": "spammer@scam.com",
    "to": "user@example.com",
    "subject": "恭喜您中了500万大奖",
    "isSpam": true,
    "spamScore": 0.5559,
    "folder": "SPAM",
    "status": "RECEIVED"
}
```

**同步测试模式（自动等待检测完成）**：
```bash
curl -s -X POST http://localhost:8080/api/mail/test-spam \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@spam.com",
    "subject": "免费领取百万大奖",
    "content": "恭喜您中了100万！点击 http://123.45.67.89/claim 领取奖金，限时优惠！"
  }' | python3 -m json.tool
```

**手动重新检测**：
```bash
curl -s -X POST http://localhost:8080/api/mail/{id}/recheck-spam | python3 -m json.tool
```

### 8.2 数据库直接验证

```bash
mysql -u root -p mail_system -e \
  "SELECT id, is_spam, spam_score, folder, SUBSTRING(subject,1,25) AS subject FROM mail ORDER BY id DESC LIMIT 5;"
```

预期输出：
```
+----+---------+------------+--------+----------------------------+
| id | is_spam | spam_score | folder | subject                    |
+----+---------+------------+--------+----------------------------+
|  5 |       1 |     0.5559 | SPAM   | 恭喜您中了500万大奖        |
|  4 |       0 |     0.2412 | INBOX  | 项目周会通知               |
+----+---------+------------+--------+----------------------------+
```

### 8.3 命令行直接测试 Python 插件（不启动后端）

```bash
cd backend

# 测试垃圾邮件检测
python3 python_plugins/bridge_spam.py \
  '{"from":"spam@test.com","subject":"中奖通知","content":"恭喜您中了100万！"}' \
  '{}'

# 测试安全分析
python3 python_plugins/bridge_security.py \
  '{"from":"security@paypa1.com","subject":"您的账户有异常登录","content":"请立即点击 http://192.168.1.1/verify 验证您的账户"}' \
  '{}'

# 测试优先级排序
python3 python_plugins/bridge_priority.py \
  '{"from":"boss@company.com","subject":"紧急：Q2财报","content":"请尽快提交Q2财务报告。","current_user":"user@company.com"}' \
  '{}'
```

---

## 九、模型训练

垃圾邮件 ML 插件使用 TF-IDF + 朴素贝叶斯分类器，支持自定义训练数据。

### 训练命令

```bash
cd backend/python_plugins/spam_ml_plugin

# 使用默认训练数据（data/train_data.json）
python3 model_train.py

# 使用自定义训练数据
python3 model_train.py --train-data data/train_data.json

# 指定模型输出目录
python3 model_train.py --train-data data/train_data.json --model-dir ./models
```

### 训练数据格式（JSON）

```json
[
  {
    "content": "恭喜您获得百万大奖，点击领取！",
    "label": 1
  },
  {
    "content": "今天的项目会议在会议室A召开。",
    "label": 0
  }
]
```

- `label`: `0` = 正常邮件, `1` = 垃圾邮件
- 建议正负样本各 100+ 条，模型即可达到较好效果

### 模型文件

训练完成后在 `models/` 目录生成：
- `vectorizer.pkl` — TF-IDF 向量化器
- `classifier.pkl` — 朴素贝叶斯分类器

这两个 `.pkl` 文件会被 `MLSpamDetector.init()` 自动加载。**不要提交到 Git**（已在 .gitignore 中排除）。

### 评估模型

```bash
python3 evaluate.py --test-data data/test_data.json --model-dir ./models
```

输出：准确率、精确率、召回率、F1 分数。

---

## 十、完整启动流程

新开发者 clone 项目后，按以下步骤启动：

### 1. 环境要求

| 组件 | 版本 |
|------|------|
| Java | 17+ |
| MySQL | 8.0+ |
| Python | 3.9+ |
| Maven | 3.8+（或使用项目自带 `./mvnw`） |

### 2. 创建数据库

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS mail_system DEFAULT CHARACTER SET utf8mb4;"
mysql -u root -p mail_system < sql/schema.sql
```

### 3. 配置敏感文件（不提交 Git）

```bash
cd backend

# 复制 template 并填入自己的配置
cp src/main/resources/application.yml.template src/main/resources/application.yml
cp python_plugins/plugins_config.json.template python_plugins/plugins_config.json
```

编辑两个文件，填入：
- MySQL 用户名/密码
- LLM API Key（可选，不填则自动降级为纯规则模式）

### 4.（可选）训练 ML 模型

```bash
cd backend/python_plugins/spam_ml_plugin
python3 model_train.py
cd ../..
```

### 5. 启动后端

```bash
cd backend
./mvnw spring-boot:run
# 或: mvn spring-boot:run
```

启动成功日志：
```
Started BackendApplication in X.XXX seconds
Tomcat started on port 8080
```

### 6. 验证功能

```bash
# 发送测试邮件
curl -s -X POST http://localhost:8080/api/mail/receive \
  -H "Content-Type: application/json" \
  -d '{"from":"test@example.com","to":"user@example.com","subject":"Hello","content":"测试内容"}' \
  | python3 -m json.tool

# 等待2-3秒后查询（替换实际ID）
curl -s http://localhost:8080/api/mail/1 | python3 -m json.tool
# 预期：isSpam 为 false（正常邮件），spamScore < 0.3
```
