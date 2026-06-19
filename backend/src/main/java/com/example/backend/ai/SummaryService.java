package com.example.backend.ai;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * 邮件摘要生成服务 - 封装对 bridge_summary.py 的调用
 * 使用 LLM 大模型生成邮件摘要，LLM 不可用时自动降级为提取式摘要
 */
@Service
public class SummaryService {

    private static final Logger log = LoggerFactory.getLogger(SummaryService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String SCRIPT_NAME = "bridge_summary.py";

    private final PythonBridge bridge;

    public SummaryService(PythonBridge bridge) {
        this.bridge = bridge;
    }

    /**
     * 生成邮件摘要
     *
     * @param emailId     邮件ID
     * @param fromAddress 发件人
     * @param subject     主题
     * @param content     正文
     * @return 摘要结果 Map（包含 summary, method 等）
     */
    public Map<String, Object> summarize(Long emailId, String fromAddress,
                                          String subject, String content) {
        return summarize(emailId, fromAddress, subject, content, 120);
    }

    /**
     * 生成邮件摘要（可指定最大长度）
     *
     * @param emailId      邮件ID
     * @param fromAddress  发件人
     * @param subject      主题
     * @param content      正文
     * @param maxLength    摘要最大长度（字符数）
     * @return 摘要结果 Map（包含 summary, method, length 等）
     */
    public Map<String, Object> summarize(Long emailId, String fromAddress,
                                          String subject, String content,
                                          int maxLength) {
        Map<String, Object> payload = new java.util.HashMap<>(Map.of(
                "id", emailId != null ? emailId : 0,
                "from", fromAddress != null ? fromAddress : "",
                "subject", subject != null ? subject : "",
                "content", content != null ? content : ""
        ));
        payload.put("summary_max_length", maxLength);

        try {
            String json = MAPPER.writeValueAsString(payload);
            return bridge.execute(SCRIPT_NAME, json);
        } catch (JsonProcessingException e) {
            log.error("JSON 序列化失败: {}", e.getMessage());
            return Map.of("error", "JSON 序列化失败: " + e.getMessage());
        }
    }
}
