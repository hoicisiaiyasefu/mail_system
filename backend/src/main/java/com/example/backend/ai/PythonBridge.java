package com.example.backend.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import jakarta.annotation.PostConstruct;

/**
 * Python 桥接器 - 通过进程调用 Python 脚本执行插件逻辑
 * 从 application.yml 读取 plugin.*、llm.*、plugins.* 配置，
 * 并传递给 Python 端的 PluginRegistry。
 */
@Component
public class PythonBridge {

    private static final Logger log = LoggerFactory.getLogger(PythonBridge.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final long TIMEOUT_SECONDS = 30;

    @Value("${plugin.python-path:python3}")
    private String pythonPath;

    /**
     * 根据操作系统自动选择 Python 命令。
     * 仅在未显式覆盖默认值 "python3" 时才调整。
     */
    @PostConstruct
    private void autoDetectPythonPath() {
        boolean isWindows = System.getProperty("os.name").toLowerCase().contains("windows");
        if ("python3".equals(pythonPath) && isWindows) {
            pythonPath = "python";
            log.info("检测到 Windows 系统，python-path 自动切换为: {}", pythonPath);
        } else {
            log.debug("python-path: {} (os: {})", pythonPath, System.getProperty("os.name"));
        }
    }

    @Value("${plugin.plugins-dir:python_plugins}")
    private String pluginsDir;

    @Value("${plugin.config-file:python_plugins/plugins_config.json}")
    private String configFile;

    // LLM 配置
    @Value("${llm.enabled:false}")
    private boolean llmEnabled;

    @Value("${llm.api-key:}")
    private String llmApiKey;

    @Value("${llm.provider:openai}")
    private String llmProvider;

    @Value("${llm.model:gpt-3.5-turbo}")
    private String llmModel;

    @Value("${llm.base-url:}")
    private String llmBaseUrl;

    // 各插件启用状态
    @Value("${plugins.email_priority_plugin.enabled:true}")
    private boolean priorityEnabled;

    @Value("${plugins.security_ai_plugin.enabled:true}")
    private boolean securityEnabled;

    @Value("${plugins.spam_ml_plugin.enabled:true}")
    private boolean spamEnabled;

    /**
     * 构建传递给 Python 端的完整插件配置 JSON
     */
    private String buildPluginConfigJson() {
        try {
            Map<String, Object> config = new HashMap<>();

            // LLM 配置
            Map<String, Object> llmCfg = new HashMap<>();
            llmCfg.put("enabled", llmEnabled);
            llmCfg.put("api_key", llmApiKey);
            llmCfg.put("provider", llmProvider);
            llmCfg.put("model", llmModel);
            if (llmBaseUrl != null && !llmBaseUrl.isBlank()) {
                llmCfg.put("base_url", llmBaseUrl);
            }
            config.put("llm", llmCfg);

            // 插件配置
            Map<String, Object> plugins = new HashMap<>();
            plugins.put("email_priority_plugin", Map.of("enabled", priorityEnabled));
            plugins.put("security_ai_plugin", Map.of("enabled", securityEnabled));
            plugins.put("spam_ml_plugin", Map.of("enabled", spamEnabled));
            config.put("plugins", plugins);

            return MAPPER.writeValueAsString(config);

        } catch (Exception e) {
            log.error("构建插件配置 JSON 失败: {}", e.getMessage());
            return "{}";
        }
    }

    /**
     * 执行 Python 桥接脚本，传入 JSON 数据和插件配置，返回解析后的 Map
     *
     * @param scriptName  脚本文件名（如 bridge_spam.py）
     * @param jsonPayload JSON 字符串参数
     * @return 解析后的结果 Map，出错时包含 "error" 键
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> execute(String scriptName, String jsonPayload) {
        try {
            String scriptPath = pluginsDir + "/" + scriptName;
            String configJson = buildPluginConfigJson();
            log.debug("执行 Python 脚本: {} {} (with config)", pythonPath, scriptPath);

            // 传递两个参数: 邮件数据 JSON + 插件配置 JSON
            ProcessBuilder pb = new ProcessBuilder(
                    pythonPath, scriptPath, jsonPayload, configJson
            );
            pb.redirectErrorStream(true);

            Process process = pb.start();
            StringBuilder output = new StringBuilder();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line);
                }
            }

            boolean finished = process.waitFor(TIMEOUT_SECONDS, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                return Map.of("error", "Python 脚本执行超时 (" + TIMEOUT_SECONDS + "s): " + scriptName);
            }

            String raw = output.toString().trim();
            if (raw.isEmpty()) {
                return Map.of("error", "Python 脚本无输出: " + scriptName);
            }

            return MAPPER.readValue(raw, Map.class);

        } catch (Exception e) {
            log.error("Python 桥接调用失败: script={}, error={}", scriptName, e.getMessage());
            return Map.of("error", "桥接调用异常: " + e.getMessage());
        }
    }
}
