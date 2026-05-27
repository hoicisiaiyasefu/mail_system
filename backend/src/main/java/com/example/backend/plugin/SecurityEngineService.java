package com.example.backend.plugin;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * AI 安全检测服务 - 封装对 bridge_security.py 的调用
 */
@Service
public class SecurityEngineService {

    private static final Logger log = LoggerFactory.getLogger(SecurityEngineService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String SCRIPT_NAME = "bridge_security.py";

    private final PythonBridge bridge;

    public SecurityEngineService(PythonBridge bridge) {
        this.bridge = bridge;
    }

    /**
     * 分析邮件的安全威胁
     *
     * @param emailId      邮件ID
     * @param fromAddress  发件人
     * @param toAddress    收件人
     * @param subject      主题
     * @param content      正文
     * @param headers      邮件头信息
     * @param attachments  附件列表
     * @return 安全分析结果 Map（包含 risk_level, threats, malicious_links 等）
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> analyze(Long emailId, String fromAddress,
                                        String toAddress, String subject,
                                        String content,
                                        Map<String, String> headers,
                                        List<Map<String, Object>> attachments) {
        Map<String, Object> payload = Map.of(
                "id", emailId != null ? emailId : 0,
                "from", fromAddress != null ? fromAddress : "",
                "to", toAddress != null ? toAddress : "",
                "subject", subject != null ? subject : "",
                "content", content != null ? content : "",
                "headers", headers != null ? headers : Map.of(),
                "attachments", attachments != null ? attachments : List.of()
        );

        try {
            String json = MAPPER.writeValueAsString(payload);
            return bridge.execute(SCRIPT_NAME, json);
        } catch (JsonProcessingException e) {
            log.error("JSON 序列化失败: {}", e.getMessage());
            return Map.of("error", "JSON 序列化失败: " + e.getMessage());
        }
    }
}