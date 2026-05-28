# Java 插件调用层

Spring Boot 后端与 Python 智能插件之间的桥接层，负责通过进程调用将邮件数据传递给 Python 插件引擎并解析返回结果。

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Spring Boot 后端                            │
│                                                                 │
│  Controller/REST API                                            │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │SpamDetector     │  │SecurityEngine    │  │PriorityEngine  │  │
│  │Service.java     │  │Service.java      │  │Service.java    │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘  │
│           │                    │                     │          │
│           └────────────────────┼─────────────────────┘          │
│                                │                                │
│                                ▼                                │
│                    ┌───────────────────────┐                    │
│                    │    PythonBridge.java   │                    │
│                    │  (ProcessBuilder 调用)  │                    │
│                    └───────────┬───────────┘                    │
│                                │ subprocess                     │
│                                ▼                                │
│              bridge_*.py  ← 命令行传 JSON                        │
│                   │                                             │
│                   ▼                                             │
│            PluginRegistry                                       │
│            (LLM 共享 + 插件调度)                                  │
└─────────────────────────────────────────────────────────────────┘
```

**调用链**：

```
Spring Controller → *Service.java → PythonBridge.java → bridge_*.py → PluginRegistry → 具体引擎
```

---

## 文件说明

### PythonBridge.java

**位置**: `com.example.backend.ai.PythonBridge`
**注解**: `@Component`

底层桥接器，负责通过 `ProcessBuilder` 启动 Python 子进程，传递 JSON 数据，读取 stdout 结果。

**核心方法**：

```java
public Map<String, Object> execute(String scriptName, String jsonPayload)
```

| 参数 | 说明 |
|------|------|
| `scriptName` | Python 桥接脚本名（如 `bridge_spam.py`） |
| `jsonPayload` | 邮件数据 JSON 字符串 |

| 返回值 | 说明 |
|--------|------|
| `Map<String, Object>` | Python 端返回的解析结果，出错时包含 `"error"` 键 |

**工作机制**：
1. 从 `application.yml` 读取 `plugin.python-path`、`plugin.plugins-dir` 等配置
2. 调用 `buildPluginConfigJson()` 构建完整的插件配置 JSON（含 LLM 参数和插件开关）
3. 执行命令：`python3 bridge_xxx.py '<邮件JSON>' '<配置JSON>'`
4. 设置 30 秒超时，超时后强制终止子进程
5. 读取 stdout 并解析为 `Map<String, Object>`

**配置注入**（从 `application.yml`）：

```java
@Value("${plugin.python-path:python3}")     // Python 解释器路径
private String pythonPath;

@Value("${plugin.plugins-dir:python_plugins}")  // 插件目录
private String pluginsDir;

@Value("${llm.enabled:false}")              // LLM 开关
private boolean llmEnabled;

@Value("${llm.api-key:}")                   // LLM API Key
private String llmApiKey;

@Value("${plugins.spam_ml_plugin.enabled:true}")  // 垃圾邮件插件开关
private boolean spamEnabled;
// ... 类似 securityEnabled, priorityEnabled
```

---

### SpamDetectorService.java

**位置**: `com.example.backend.ai.SpamDetectorService`
**注解**: `@Service`

垃圾邮件检测服务，封装对 `bridge_spam.py` 的调用。

**核心方法**：

```java
public Map<String, Object> detect(
    Long emailId,
    String fromAddress,
    String toAddress,
    String subject,
    String content
)
```

| 参数 | 说明 |
|------|------|
| `emailId` | 邮件 ID |
| `fromAddress` | 发件人地址 |
| `toAddress` | 收件人地址 |
| `subject` | 邮件主题 |
| `content` | 邮件正文 |

| 返回字段 | 类型 | 说明 |
|---------|------|------|
| `is_spam` | Boolean | 是否垃圾邮件 |
| `spam_score` | Number | 垃圾邮件置信度 (0~1) |
| `result` | String | 详细判定说明 |

**使用示例**：

```java
@Autowired
private SpamDetectorService spamDetector;

public void checkEmail(Email email) {
    Map<String, Object> result = spamDetector.detect(
        email.getId(),
        email.getFromAddress(),
        email.getToAddress(),
        email.getSubject(),
        email.getContent()
    );
    
    boolean isSpam = (Boolean) result.get("is_spam");
    double score = ((Number) result.get("spam_score")).doubleValue();
    // 根据结果决定是否标记为垃圾邮件
}
```

---

### SecurityEngineService.java

**位置**: `com.example.backend.ai.SecurityEngineService`
**注解**: `@Service`

AI 安全检测服务，封装对 `bridge_security.py` 的调用。

**核心方法**：

```java
public Map<String, Object> analyze(
    Long emailId,
    String fromAddress,
    String toAddress,
    String subject,
    String content,
    Map<String, String> headers,
    List<Map<String, Object>> attachments
)
```

| 参数 | 说明 |
|------|------|
| `emailId` | 邮件 ID |
| `fromAddress` | 发件人地址 |
| `toAddress` | 收件人地址 |
| `subject` | 邮件主题 |
| `content` | 邮件正文 |
| `headers` | 邮件原始头信息（可选） |
| `attachments` | 附件列表（可选） |

| 返回字段 | 类型 | 说明 |
|---------|------|------|
| `risk_level` | String | safe / low / medium / high / critical |
| `risk_score` | Number | 综合风险评分 (0~1) |
| `is_spoofed` | Boolean | 是否伪造发件人 |
| `threats` | List | 威胁列表 `[{type, detail}]` |
| `malicious_links` | List | 恶意链接 `[{url, reason}]` |
| `recommendation` | String | 处理建议 |

**使用示例**：

```java
@Autowired
private SecurityEngineService securityEngine;

public void analyzeEmail(Email email) {
    Map<String, Object> result = securityEngine.analyze(
        email.getId(),
        email.getFromAddress(),
        email.getToAddress(),
        email.getSubject(),
        email.getContent(),
        email.getHeaders(),      // Map<String, String>
        email.getAttachments()   // List<Map<String, Object>>
    );
    
    String riskLevel = (String) result.get("risk_level");
    if ("high".equals(riskLevel) || "critical".equals(riskLevel)) {
        // 高风险邮件：标记警告或隔离
        log.warn("检测到高风险邮件: {}", result.get("threats"));
    }
}
```

---

### PriorityEngineService.java

**位置**: `com.example.backend.ai.PriorityEngineService`
**注解**: `@Service`

邮件优先级排序服务，封装对 `bridge_priority.py` 的调用。

**核心方法**：

```java
public Map<String, Object> score(
    Long emailId,
    String fromAddress,
    String toAddress,
    String subject,
    String content,
    String currentUser
)
```

| 参数 | 说明 |
|------|------|
| `emailId` | 邮件 ID |
| `fromAddress` | 发件人地址 |
| `toAddress` | 收件人地址 |
| `subject` | 邮件主题 |
| `content` | 邮件正文 |
| `currentUser` | 当前登录用户标识 |

| 返回字段 | 类型 | 说明 |
|---------|------|------|
| `priority_score` | Number | 优先级评分 (0~1) |
| `priority_level` | String | critical / high / normal / low |
| `suggestion` | String | 处理建议 |

**使用示例**：

```java
@Autowired
private PriorityEngineService priorityEngine;

public void scoreEmail(Email email, String currentUser) {
    Map<String, Object> result = priorityEngine.score(
        email.getId(),
        email.getFromAddress(),
        email.getToAddress(),
        email.getSubject(),
        email.getContent(),
        currentUser
    );
    
    String level = (String) result.get("priority_level");
    double score = ((Number) result.get("priority_score")).doubleValue();
    // 根据优先级排序收件箱
}
```

---

## 在 Controller 中集成使用

典型的 REST Controller 使用模式：

```java
@RestController
@RequestMapping("/api/emails")
public class EmailController {

    @Autowired
    private SpamDetectorService spamDetector;
    
    @Autowired
    private SecurityEngineService securityEngine;
    
    @Autowired
    private PriorityEngineService priorityEngine;

    /**
     * 接收新邮件时，一站式调用三个插件进行分析
     */
    @PostMapping("/analyze/{id}")
    public ResponseEntity<Map<String, Object>> analyzeEmail(
            @PathVariable Long id,
            @RequestBody EmailRequest request,
            @RequestHeader("X-Current-User") String currentUser) {
        
        Map<String, Object> response = new HashMap<>();
        
        // 1. 垃圾邮件检测
        Map<String, Object> spamResult = spamDetector.detect(
            id, request.from(), request.to(),
            request.subject(), request.content()
        );
        response.put("spam", spamResult);
        
        // 2. 安全威胁分析
        Map<String, Object> securityResult = securityEngine.analyze(
            id, request.from(), request.to(),
            request.subject(), request.content(),
            request.headers(), request.attachments()
        );
        response.put("security", securityResult);
        
        // 3. 优先级排序
        Map<String, Object> priorityResult = priorityEngine.score(
            id, request.from(), request.to(),
            request.subject(), request.content(), currentUser
        );
        response.put("priority", priorityResult);
        
        return ResponseEntity.ok(response);
    }
}
```

---

## application.yml 配置详解

```yaml
# ==========================================
# Python 智能插件配置
# ==========================================
plugin:
  python-path: python3                           # Python 解释器路径
  plugins-dir: python_plugins                     # 插件目录（相对于 backend/）
  config-file: python_plugins/plugins_config.json # 可选，JSON 配置文件

# ==========================================
# 大模型（LLM）配置 - 可选
# ==========================================
llm:
  enabled: false               # 是否启用大模型
  api-key: ""                  # API 密钥（开启时必填）
  provider: openai             # 提供商：openai | custom
  model: gpt-3.5-turbo         # 模型名称
  base-url: ""                 # 自定义 API 地址，留空用默认

# ==========================================
# 各插件开关
# ==========================================
plugins:
  spam_ml_plugin:
    enabled: true              # 垃圾邮件检测
  security_ai_plugin:
    enabled: true              # 安全威胁分析
  email_priority_plugin:
    enabled: true              # 优先级排序

# ==========================================
# 日志级别（调试用）
# ==========================================
logging:
  level:
    com.example.backend.ai: DEBUG   # 输出 PythonBridge 详细日志
```

---

## 启用 LLM 大模型的操作步骤

### 步骤 1：获取 API Key

选择一个 LLM 服务并获取 API Key：

- **OpenAI 官方**：访问 https://platform.openai.com/api-keys 创建密钥
- **Ollama 本地**：`ollama pull qwen2.5:7b`（免费，无需 API Key，但仍需填写一个占位值）
- **其他兼容 API**：按服务商指引获取

### 步骤 2：修改 application.yml

```yaml
llm:
  enabled: true
  api-key: "sk-your-actual-api-key-here"
  provider: openai              # 或 custom
  model: gpt-3.5-turbo          # 或 qwen2.5:7b / deepseek-chat 等
  base-url: ""                  # 如用 Ollama: "http://localhost:11434/v1"
```

### 步骤 3：（可选）安装 OpenAI SDK

如果 `provider` 设为 `openai`，建议安装官方 SDK：

```bash
pip install openai
```

如果不安装，系统会自动 fallback 到纯 HTTP 方式（`provider: custom`），功能相同。

### 步骤 4：重启 Spring Boot 应用

```bash
cd mail_system/backend
./mvnw spring-boot:run
```

观察启动日志：

```
已加载插件配置: python_plugins/plugins_config.json
LLM 功能已启用: openai/gpt-3.5-turbo
OpenAI SDK 连接成功: openai/gpt-3.5-turbo
插件已加载: spam_ml_plugin (MLSpamDetector)
插件已加载: security_ai_plugin (SecurityEngine)
插件已加载: email_priority_plugin (PriorityEngine)
插件注册表初始化完成, LLM: 已启用
```

### 步骤 5：验证

发送一封测试邮件，观察日志中 Python 桥接调用的输出。安全引擎和优先级引擎的检测结果将包含 LLM 增强的语义分析内容。

---

## 异常处理

所有 Service 方法在 Python 脚本执行失败时，返回的 Map 中会包含 `"error"` 键：

```java
Map<String, Object> result = spamDetector.detect(...);
if (result.containsKey("error")) {
    log.error("垃圾邮件检测失败: {}", result.get("error"));
    // 可降级处理：默认不作为垃圾邮件
}
```

常见错误场景：
- Python 脚本执行超时（30 秒）
- JSON 解析失败
- 插件未加载（配置中 `enabled: false`）
- LLM API 连接失败（自动降级为规则模式）

---

## 注意事项

1. **性能**：每次调用都会启动一个新的 Python 子进程，有进程创建开销。对于高并发场景，可考虑改为常驻 Python 服务（如 HTTP/gRPC），但当前 ProcessBuilder 方案更简单可靠
2. **路径**：`plugins-dir` 的相对路径基准是 Spring Boot 的工作目录（即 `backend/`），确保 `python_plugins/` 目录在正确位置
3. **Python 环境**：确保 `python3` 命令可用，且已安装必要的依赖（`pip install openai` 可选）
4. **编码**：所有 JSON 通信使用 UTF-8 编码，`ProcessBuilder` 已配置 `StandardCharsets.UTF_8`