package com.example.backend.ai;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * 垃圾邮件检测服务 - 封装对 bridge_spam.py 的调用
 */
@Service
public class SpamDetectorService {

    private static final Logger log = LoggerFactory.getLogger(SpamDetectorService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String SCRIPT_NAME = "bridge_spam.py";

    private final PythonBridge bridge;

    public SpamDetectorService(PythonBridge bridge) {
        this.bridge = bridge;
    }

    /**
     * 检测邮件是否为垃圾邮件
     *
     * @param emailId      邮件ID
     * @param fromAddress  发件人
     * @param toAddress    收件人
     * @param subject      主题
     * @param content      正文
     * @return 检测结果 Map
     */
    public Map<String, Object> detect(Long emailId, String fromAddress,
                                       String toAddress, String subject,
                                       String content) {
        Map<String, Object> payload = Map.of(
                "id", emailId != null ? emailId : 0,
                "from", fromAddress != null ? fromAddress : "",
                "to", toAddress != null ? toAddress : "",
                "subject", subject != null ? subject : "",
                "content", content != null ? content : ""
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