package com.example.backend.controller;

import com.example.backend.entity.Mail;
import com.example.backend.entity.MailUser;
import com.example.backend.service.MailService;
import com.example.backend.service.SpamAsyncService;
import com.example.backend.util.JwtUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 邮件接口 - 邮件接收、查询与垃圾邮件检测
 */
@RestController
@RequestMapping("/api/mail")
@CrossOrigin(origins = "*")
public class MailController {

    private final MailService mailService;
    private final SpamAsyncService spamAsyncService;

    public MailController(MailService mailService, SpamAsyncService spamAsyncService) {
        this.mailService = mailService;
        this.spamAsyncService = spamAsyncService;
    }

    /**
     * 接收新邮件 - 保存后自动在后台触发 AI 垃圾邮件检测
     * POST /api/mail/receive
     */
    @PostMapping("/receive")
    public ResponseEntity<Map<String, Object>> receiveMail(@RequestBody Map<String, Object> body) {
        try {
            String fromAddress = (String) body.getOrDefault("from", "");
            String toAddresses = (String) body.getOrDefault("to", "");
            String subject = (String) body.getOrDefault("subject", "");
            String content = (String) body.getOrDefault("content", "");
            String contentType = (String) body.getOrDefault("contentType", "text/plain");

            if (fromAddress.isBlank() || toAddresses.isBlank()) {
                return ResponseEntity.badRequest().body(Map.of(
                        "error", "发件人和收件人不能为空"
                ));
            }

            Mail savedMail = mailService.receiveMail(fromAddress, toAddresses, subject, content, contentType);

            return ResponseEntity.ok(Map.of(
                    "id", savedMail.getId(),
                    "from", savedMail.getFromAddress(),
                    "to", savedMail.getToAddresses(),
                    "subject", savedMail.getSubject(),
                    "status", "RECEIVED",
                    "message", "邮件已接收，AI 正在后台检测垃圾邮件..."
            ));

        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "邮件接收失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 查询单封邮件（含 is_spam 状态）
     * GET /api/mail/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getMail(@PathVariable Long id) {
        Mail mail = mailService.findById(id);
        if (mail == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(Map.of(
                "id", mail.getId(),
                "from", mail.getFromAddress(),
                "to", mail.getToAddresses(),
                "subject", mail.getSubject(),
                "content", mail.getContent(),
                "isSpam", mail.getIsSpam(),
                "spamScore", mail.getSpamScore(),
                "folder", mail.getFolder().name(),
                "status", mail.getStatus().name(),
                "receivedAt", mail.getReceivedAt() != null ? mail.getReceivedAt().toString() : null
        ));
    }

    /**
     * 测试垃圾邮件检测（同步模式，方便调试）
     * POST /api/mail/test-spam
     */
    @PostMapping("/test-spam")
    public ResponseEntity<Map<String, Object>> testSpamDetection(@RequestBody Map<String, Object> body) {
        try {
            String fromAddress = (String) body.getOrDefault("from", "test@spam.com");
            String toAddresses = (String) body.getOrDefault("to", "user@example.com");
            String subject = (String) body.getOrDefault("subject", "测试邮件");
            String content = (String) body.getOrDefault("content", "这是一封测试邮件");
            String contentType = (String) body.getOrDefault("contentType", "text/plain");

            Mail savedMail = mailService.receiveMail(fromAddress, toAddresses, subject, content, contentType);

            // 等待一小段时间让异步检测完成
            Thread.sleep(3000);

            // 重新查询获取最新的 is_spam 状态
            Mail updated = mailService.findById(savedMail.getId());

            return ResponseEntity.ok(Map.of(
                    "id", savedMail.getId(),
                    "isSpam", updated != null ? updated.getIsSpam() : false,
                    "spamScore", updated != null ? updated.getSpamScore() : 0.0,
                    "folder", updated != null ? updated.getFolder().name() : "INBOX",
                    "from", savedMail.getFromAddress(),
                    "subject", savedMail.getSubject()
            ));

        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "检测失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 重新检测邮件垃圾状态（手动触发）
     * POST /api/mail/{id}/recheck-spam
     */
    @PostMapping("/{id}/recheck-spam")
    public ResponseEntity<Map<String, Object>> recheckSpam(@PathVariable Long id) {
        Mail mail = mailService.findById(id);
        if (mail == null) {
            return ResponseEntity.notFound().build();
        }

        spamAsyncService.detectAndUpdate(mail);

        return ResponseEntity.ok(Map.of(
                "id", mail.getId(),
                "message", "已触发异步重新检测，请稍后查询结果"
        ));
    }

    /**
     * 发送邮件 — 需登录（JWT Token）
     * POST /api/mail/send
     *
     * <p>请求头：Authorization: Bearer &lt;token&gt;</p>
     *
     * <p>请求体 JSON：</p>
     * <pre>{@code
     * {
     *   "to": "lisi@example.com",
     *   "subject": "会议通知",
     *   "content": "周五下午开会...",
     *   "cc": "wangwu@example.com"
     * }
     * }</pre>
     *
     * <p>成功响应：</p>
     * <pre>{@code
     * {
     *   "id": 10,
     *   "from": "zhangsan@example.com",
     *   "to": "lisi@example.com",
     *   "subject": "会议通知",
     *   "status": "SENT",
     *   "message": "邮件已发送"
     * }
     * }</pre>
     */
    @PostMapping("/send")
    public ResponseEntity<Map<String, Object>> sendMail(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestBody Map<String, Object> body) {

        // 1. 校验 Token
        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long senderUserId = JwtUtil.getUserIdFromToken(token);

        // 2. 解析请求参数
        String to      = (String) body.get("to");
        String subject = (String) body.get("subject");
        String content = (String) body.get("content");
        String cc      = (String) body.get("cc");   // 可选

        if (to == null || to.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "收件人不能为空"
            ));
        }
        if (subject == null || subject.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "邮件主题不能为空"
            ));
        }

        // 3. 调用业务层发送
        try {
            Map<String, Object> result = mailService.sendMail(
                    senderUserId, to, subject,
                    content != null ? content : "",
                    cc != null ? cc : ""
            );
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "邮件发送失败: " + e.getMessage()
            ));
        }
    }

    // ============================================================
    // 私有辅助方法
    // ============================================================

    /**
     * 从 Authorization 请求头中提取 Bearer Token
     */
    private String extractBearerToken(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        return null;
    }
}