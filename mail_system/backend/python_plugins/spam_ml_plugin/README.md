# ML Spam Detector Plugin (邮件垃圾邮件检测插件)

基于机器学习的垃圾邮件检测插件，实现 EmailPluginBase 接口，可插拔式集成到邮件服务器中。

## 功能特性

- **TF-IDF + 朴素贝叶斯**：核心 ML 分类器，支持中英文混合邮件
- **规则引擎辅助**：关键词、URL 检测、大写占比等启发式规则
- **DLL 加速**：支持通过 C++ DLL 加载 ONNX 模型进行高性能推理
- **自动回退**：DLL 不可用时自动回退到 Python 纯实现
- **实时处理**：邮件到达时同步检测（`is_async = False`）
- **插件化接口**：继承 EmailPluginBase，标准化 init/process/shutdown

## 目录结构

```
spam_ml_plugin/
├── __init__.py              # 包初始化，暴露工厂函数
├── plugin_interface.py      # 插件统一接口基类 (EmailPluginBase)
├── ml_spam_detector.py      # 核心检测器实现
├── model_train.py           # 模型训练脚本
├── requirements.txt         # Python 依赖
├── README.md                # 本文件
├── models/                  # 模型存储目录 (.pkl)
└── spam_ml_core/            # C++ DLL 源码（可选）
    ├── onnx_inference.cpp   # ONNX 推理 DLL
    └── CMakeLists.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 训练模型

```bash
cd spam_ml_plugin
python model_train.py --use-synthetic
```

### 3. 作为插件使用

```python
from spam_ml_plugin import create_detector

# 创建并初始化插件
detector = create_detector(config={
    "model_dir": "./models",
    "dll_path": None  # 可选：指定 DLL 路径
})

# 检测邮件
result = detector.process({
    "id": "msg-001",
    "from": "sender@example.com",
    "subject": "免费赚钱机会!!!",
    "content": "恭喜中奖！点击 http://scam.example.com 领取...",
})

print(f"是否垃圾邮件: {result['is_spam']}")
print(f"置信度: {result['confidence']}")
print(f"结果: {result['result']}")

# 关闭插件
detector.shutdown()
```

### 4. DLL 编译（可选）

```bash
cd spam_ml_core
cmake -B build
cmake --build build --config Release
# 生成的 spam_inference.dll 会被 Python 端自动加载
```

## 接口说明

### EmailPluginBase

所有插件必须实现的基类接口：

| 方法 | 说明 |
|------|------|
| `init(config)` | 初始化，传入配置字典 |
| `process(email_data)` | 实时处理邮件 |
| `process_async(email_data, callback)` | 异步处理（可选重写） |
| `shutdown()` | 释放资源 |
| `get_info()` | 返回插件元信息 |

### 邮件数据格式 (email_data)

```python
{
    "id": str,           # 邮件ID
    "from": str,         # 发件人
    "to": str,           # 收件人
    "subject": str,      # 主题
    "content": str,      # 正文
    "headers": dict,     # 邮件头（可选）
    "attachments": list, # 附件（可选）
}
```

### 处理结果格式

```python
{
    "plugin_name": "ml_spam_detector",
    "is_spam": bool,
    "confidence": float,      # 0.0 ~ 1.0
    "spam_score": float,      # 0.0 ~ 1.0
    "rule_features": dict,
    "result": str,            # 人类可读描述
}