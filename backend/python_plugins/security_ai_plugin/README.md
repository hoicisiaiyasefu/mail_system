# Security AI Plugin (安全与多媒体处理 AI 插件)

基于规则引擎 + 大模型的邮件安全威胁检测插件，实现 EmailPluginBase 接口，可插拔式集成。

## 功能特性

### 五大检测维度

| 检测模块 | 功能 | 检测内容 |
|----------|------|----------|
| **SpoofDetector** | 伪造发件人检测 | SPF/DKIM 模拟验证 + 显示名欺诈 + Reply-To 不一致 |
| **LinkAnalyzer** | 恶意链接分析 | 短链接识别 + 域名仿冒 + URL认证伪装(@符号) + 重定向检测 |
| **ThreatDetector** | 钓鱼邮件识别 | 5 类关键词匹配 + URL 可疑分析 + 域名仿冒 + 附件检查 |
| **附件安全** | 恶意附件检测 | 高危扩展名 + 双重扩展名伪装 + 文件大小异常 |
| **LLM 深度分析** | 大模型语义分析 | 社会工程学攻击 + BEC 诈骗 + 隐藏恶意链接（可选） |

### 架构特点

- **实时处理**：`is_async = False`，邮件一到就分析安全性
- **LLM 可选**：大模型深度分析由用户自行决定是否开启（填写 API Key）
- **多引擎融合**：规则引擎 + 模式匹配 + LLM，多种检测互补
- **风险量化**：0~1 风险评分 + 5 级风险等级

## 目录结构

```
security_ai_plugin/
├── __init__.py           # 包入口
├── plugin_interface.py   # 插件基类接口
├── security_engine.py    # 安全引擎主入口
├── spoof_detector.py     # 伪造发件人检测
├── link_analyzer.py      # 恶意链接分析
├── threat_detector.py    # 钓鱼/附件威胁检测
├── llm_api.py            # 大模型服务接口
├── README.md
└── data/                 # 黑白名单数据
```

## 快速开始

### 1. 基础使用

```python
from security_ai_plugin import create_security_engine

engine = create_security_engine()
result = engine.process({
    "from": "PayPal Support <phish@evil.com>",
    "to": "user@example.com",
    "subject": "紧急：您的账户已被锁定",
    "content": "请点击链接验证：http://192.168.1.1/login.php",
    "headers": {"Reply-To": "hacker@gmail.com"},
    "attachments": [],
})
print(result["risk_level"])    # 'high'
print(result["is_spoofed"])    # True
print(result["recommendation"]) # 处理建议
```

### 2. 启用 LLM 深度分析

```python
engine = create_security_engine(config={
    "llm_api_key": "sk-xxxxx",
    "llm_provider": "openai",
    "llm_model": "gpt-4",
})
```

### 3. 配置黑白名单

```python
engine = create_security_engine(config={
    "whitelist_file": "data/whitelist.txt",  # 可信发件人
    "blacklist_file": "data/blacklist.txt",  # 黑名单发件人
})
```

## 风险等级

| 等级 | 分数范围 | 处理建议 |
|------|----------|----------|
| safe | 0.0~0.1 | 邮件安全，可正常处理 |
| low | 0.1~0.3 | 标记为可疑，用户自行判断 |
| medium | 0.3~0.6 | 隔离处理，通知用户注意 |
| high | 0.6~0.8 | 移至垃圾邮件，警告用户 |
| critical | 0.8~1.0 | 立即隔离，阻止链接，通知安全团队 |