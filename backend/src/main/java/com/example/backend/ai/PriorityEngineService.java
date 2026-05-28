package com.example.backend.ai;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * 邮件优先级排序服务 - 封装对 bridge_priority.py 的调用
 */
@Service
public class PriorityEngineService {

    private static final Logger log = LoggerFactory.getLogger(PriorityEngineService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String SCRIPT_NAME = "bridge_priority.py";

    private final PythonBridge bridge;

    public PriorityEngineService(PythonBridge bridge) {
        this.bridge = bridge;
    }

    /**
     * 对邮件进行优先级评分
     *
     * @param emailId      邮件ID
     * @param fromAddress  发件人
     * @param toAddress    收件人
     * @param subject      主题
     * @param content      正文
     * @param currentUser  当前用户标识
     * @return 优先级评分结果 Map（包含 priority_score, priority_level 等）
     */
    public Map<String, Object> score(Long emailId, String fromAddress,
                                      String toAddress, String subject,
                                      String content, String currentUser) {
        Map<String, Object> payload = Map.of(
                "id", emailId != null ? emailId : 0,
                "from", fromAddress != null ? fromAddress : "",
                "to", toAddress != null ? toAddress : "",
                "subject", subject != null ? subject : "",
                "content", content != null ? content : "",
                "current_user", currentUser != null ? currentUser : "default"
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