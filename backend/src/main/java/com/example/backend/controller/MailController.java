package com.example.backend.controller;

import com.example.backend.entity.Mail;
import com.example.backend.entity.MailUser;
import com.example.backend.service.FileStorageService;
import com.example.backend.service.MailService;
import com.example.backend.service.SpamAsyncService;
import com.example.backend.util.JwtUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

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
    private final FileStorageService fileStorageService;

    public MailController(MailService mailService,
                          SpamAsyncService spamAsyncService,
                          FileStorageService fileStorageService) {
        this.mailService = mailService;
        this.spamAsyncService = spamAsyncService;
        this.fileStorageService = fileStorageService;
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
     * <p>Content-Type: multipart/form-data</p>
     *
     * <p>请求参数：</p>
     * <pre>
     *   - to: string
     *   - subject: string
     *   - content: string
     *   - cc: string (optional)
     *   - file: MultipartFile (optional)
     * </pre>
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
            @RequestParam("to") String to,
            @RequestParam("subject") String subject,
            @RequestParam("content") String content,
            @RequestParam(value = "cc", required = false) String cc,
            @RequestParam(value = "file", required = false) MultipartFile file) {

        // 1. 校验 Token
        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long senderUserId = JwtUtil.getUserIdFromToken(token);

        // 2. 校验参数
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

        // 3. 保存文件（如果有）
        String filePath = null;
        if (file != null && !file.isEmpty()) {
            filePath = fileStorageService.saveFile(file);
        }

        // 4. 调用业务层发送
        try {
            Map<String, Object> result = mailService.sendMailWithAttachment(
                    senderUserId, to, subject,
                    content != null ? content : "",
                    cc != null ? cc : "",
                    filePath
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

    @PostMapping("/receive-with-attachment")
    public ResponseEntity<Map<String, Object>> receiveWithAttachment(
            @RequestParam("from") String from,
            @RequestParam("to") String to,
            @RequestParam("subject") String subject,
            @RequestParam("content") String content,
            @RequestParam(value = "file", required = false) MultipartFile file
    ) {

        if (from == null || from.isBlank() || to == null || to.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "发件人和收件人不能为空"
            ));
        }

        String filePath = fileStorageService.saveFile(file);

        Mail mail = mailService.receiveMail(
                from, to, subject, content, "text/plain"
        );

        if (filePath != null) {
            mail.setAttachmentPath(filePath);
            mail.setHasAttachments(true);
            mailService.saveMail(mail);
        }

        return ResponseEntity.ok(Map.of(
                "msg", "ok",
                "mailId", mail.getId(),
                "filePath", filePath
        ));
    }

    @GetMapping("/list")
    public ResponseEntity<?> listInbox(@RequestHeader(value = "Authorization", required = false) String authHeader) {
        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = JwtUtil.getUserIdFromToken(token);
        try {
            var mails = mailService.listInboxByUserId(userId);
            var data = mails.stream().map(mail -> Map.<String, Object>of(
                    "id", mail.getId(),
                    "from", mail.getFromAddress(),
                    "to", mail.getToAddresses(),
                    "subject", mail.getSubject(),
                    "receivedAt", mail.getReceivedAt() != null ? mail.getReceivedAt().toString() : null,
                    "isSpam", mail.getIsSpam(),
                    "hasAttachments", mail.getHasAttachments(),
                    "attachmentPath", mail.getAttachmentPath(),
                    "folder", mail.getFolder().name(),
                    "status", mail.getStatus().name()
            )).toList();
            return ResponseEntity.ok(Map.of("mails", data));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "查询收件列表失败: " + e.getMessage()
            ));
        }
    }
}

