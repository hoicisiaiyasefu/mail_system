package com.example.backend.controller;

import com.example.backend.ai.SummaryService;
import com.example.backend.entity.Mail;
import com.example.backend.entity.MailUser;
import com.example.backend.service.FileStorageService;
import com.example.backend.service.MailService;
import com.example.backend.service.SpamAsyncService;
import com.example.backend.util.JwtUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * 邮件接口 - 邮件接收、查询、AI 分析与垃圾邮件检测
 */
@RestController
@RequestMapping("/api/mail")
@CrossOrigin(origins = "*")
public class MailController {

    private final MailService mailService;
    private final SpamAsyncService spamAsyncService;
    private final FileStorageService fileStorageService;
    private final SummaryService summaryService;

    public MailController(MailService mailService,
                          SpamAsyncService spamAsyncService,
                          FileStorageService fileStorageService,
                          SummaryService summaryService) {
        this.mailService = mailService;
        this.spamAsyncService = spamAsyncService;
        this.fileStorageService = fileStorageService;
        this.summaryService = summaryService;
    }

    /**
     * 接收新邮件 - 保存后自动在后台触发 AI 综合分析管道
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
                    "message", "邮件已接收，AI 正在后台分析（垃圾检测+安全分析+优先级+摘要）..."
            ));

        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "邮件接收失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 查询单封邮件（含 AI 分析结果）
     * GET /api/mail/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<?> getMail(@PathVariable Long id) {
        Mail mail = mailService.findById(id);
        if (mail == null) {
            return ResponseEntity.notFound().build();
        }
        java.util.Map<String, Object> resp = new java.util.HashMap<>();
        resp.put("id", mail.getId());
        resp.put("from", mail.getFromAddress());
        resp.put("to", mail.getToAddresses());
        resp.put("subject", mail.getSubject());
        resp.put("content", mail.getContent());
        resp.put("isSpam", mail.getIsSpam());
        resp.put("spamScore", mail.getSpamScore());
        resp.put("folder", mail.getFolder().name());
        resp.put("status", mail.getStatus().name());
        resp.put("readFlag", mail.getReadFlag());
        resp.put("receivedAt", mail.getReceivedAt() != null ? mail.getReceivedAt().toString() : null);
        // AI 分析字段
        resp.put("riskLevel", mail.getRiskLevel());
        resp.put("riskScore", mail.getRiskScore());
        resp.put("priorityLevel", mail.getPriorityLevel());
        resp.put("priorityScore", mail.getPriorityScore());
        resp.put("summary", mail.getSummary());
        resp.put("aiAnalyzed", mail.getAiAnalyzed());
        return ResponseEntity.ok(resp);
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

            // 等待 AI 异步分析完成
            Thread.sleep(3000);

            // 重新查询获取最新的分析状态
            Mail updated = mailService.findById(savedMail.getId());

            return ResponseEntity.ok(Map.of(
                    "id", savedMail.getId(),
                    "isSpam", updated != null ? updated.getIsSpam() : false,
                    "spamScore", updated != null ? updated.getSpamScore() : 0.0,
                    "folder", updated != null ? updated.getFolder().name() : "INBOX",
                    "riskLevel", updated != null ? updated.getRiskLevel() : null,
                    "priorityLevel", updated != null ? updated.getPriorityLevel() : null,
                    "summary", updated != null ? updated.getSummary() : null,
                    "aiAnalyzed", updated != null ? updated.getAiAnalyzed() : false,
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
     * 重新运行完整 AI 分析管道（手动触发）
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
                "message", "已触发异步 AI 综合分析管道，请稍后查询结果"
        ));
    }

    // ============================================================
    // 邮件摘要生成接口（C模块 加分项）
    // ============================================================

    /**
     * 为指定邮件生成摘要（使用 LLM，不可用时自动降级）
     * POST /api/mail/{id}/summary
     *
     * 请求体（可选）：
     * { "maxLength": 80 }   // 摘要最大长度，默认120
     */
    @PostMapping("/{id}/summary")
    public ResponseEntity<Map<String, Object>> generateSummary(
            @PathVariable Long id,
            @RequestBody(required = false) Map<String, Object> body) {

        Mail mail = mailService.findById(id);
        if (mail == null) {
            return ResponseEntity.notFound().build();
        }

        int maxLength = 120;
        if (body != null && body.containsKey("maxLength")) {
            try {
                maxLength = ((Number) body.get("maxLength")).intValue();
            } catch (Exception ignored) {
            }
        }

        Map<String, Object> result = summaryService.summarize(
                mail.getId(), mail.getFromAddress(),
                mail.getSubject(), mail.getContent(), maxLength);

        // 如果生成成功，回写到数据库
        String summaryText = (String) result.get("summary");
        if (summaryText != null && !summaryText.isBlank() && !result.containsKey("error")) {
            mail.setSummary(summaryText);
            mailService.saveMail(mail);
        }

        return ResponseEntity.ok(Map.of(
                "id", mail.getId(),
                "summary", summaryText,
                "method", result.getOrDefault("method", "unknown"),
                "length", result.getOrDefault("length", 0)
        ));
    }

    /**
     * 获取邮件 AI 分析报告
     * GET /api/mail/{id}/ai-report
     */
    @GetMapping("/{id}/ai-report")
    public ResponseEntity<Map<String, Object>> getAiReport(@PathVariable Long id) {
        Mail mail = mailService.findById(id);
        if (mail == null) {
            return ResponseEntity.notFound().build();
        }

        return ResponseEntity.ok(Map.of(
                "id", mail.getId(),
                "subject", mail.getSubject(),
                "aiAnalyzed", mail.getAiAnalyzed(),
                "spam", Map.of(
                        "isSpam", mail.getIsSpam(),
                        "spamScore", mail.getSpamScore()
                ),
                "security", Map.of(
                        "riskLevel", mail.getRiskLevel(),
                        "riskScore", mail.getRiskScore()
                ),
                "priority", Map.of(
                        "priorityLevel", mail.getPriorityLevel(),
                        "priorityScore", mail.getPriorityScore()
                ),
                "summary", Map.of(
                        "text", mail.getSummary()
                )
        ));
    }

    // ============================================================
    // 邮件发送与列表
    // ============================================================

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

    /**
     * 发送邮件（支持附件）- 需登录（JWT Token）
     * POST /api/mail/send-with-attachment
     *
     * <p>Content-Type: multipart/form-data</p>
     * <p>请求字段：to（必填）、subject（必填）、content、cc、file（可选，可传多个）</p>
     */
    @PostMapping("/send-with-attachment")
    public ResponseEntity<Map<String, Object>> sendMailWithAttachment(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestParam("to") String to,
            @RequestParam("subject") String subject,
            @RequestParam(value = "content", defaultValue = "") String content,
            @RequestParam(value = "cc", defaultValue = "") String cc,
            @RequestParam(value = "file", required = false) List<MultipartFile> files) {

        // 1. 校验 Token
        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long senderUserId = JwtUtil.getUserIdFromToken(token);

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

        try {
            // 保存附件
            List<String> attachmentPaths = new java.util.ArrayList<>();
            if (files != null) {
                for (MultipartFile file : files) {
                    if (file != null && !file.isEmpty()) {
                        String path = fileStorageService.saveFile(file);
                        if (path != null) {
                            attachmentPaths.add(path);
                        }
                    }
                }
            }

            // 调用业务层发送
            Map<String, Object> result = mailService.sendMail(
                    senderUserId, to, subject, content, cc);

            // 如果有附件，更新邮件记录
            if (!attachmentPaths.isEmpty()) {
                Long mailId = (Long) result.get("id");
                Mail mail = mailService.findById(mailId);
                if (mail != null) {
                    mail.setAttachmentPath(String.join(",", attachmentPaths));
                    mail.setHasAttachments(true);
                    mailService.saveMail(mail);
                    result.put("attachmentPath", mail.getAttachmentPath());
                    result.put("hasAttachments", true);
                }
            }

            return ResponseEntity.ok(result);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "邮件发送失败: " + e.getMessage()
            ));
        }
    }

    // ============================================================
    // B模块（基础功能扩展）：删除、标记已读、未读通知
    // ============================================================

    /**
     * 删除邮件（软删除，移到 TRASH）
     * DELETE /api/mail/delete?id=xxx
     * <p>需要登录（JWT Token）</p>
     */
    @DeleteMapping("/delete")
    public ResponseEntity<Map<String, Object>> deleteMail(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestParam("id") Long mailId) {

        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = JwtUtil.getUserIdFromToken(token);
        try {
            mailService.softDelete(mailId, userId);
            return ResponseEntity.ok(Map.of(
                    "id", mailId,
                    "status", "DELETED",
                    "message", "邮件已删除"
            ));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "删除失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 标记邮件为已读
     * POST /api/mail/read?id=xxx
     * <p>需要登录（JWT Token）</p>
     */
    @PostMapping("/read")
    public ResponseEntity<Map<String, Object>> markAsRead(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestParam("id") Long mailId) {

        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = JwtUtil.getUserIdFromToken(token);
        try {
            mailService.markAsRead(mailId, userId);
            return ResponseEntity.ok(Map.of(
                    "id", mailId,
                    "status", "READ",
                    "message", "已标记为已读"
            ));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "标记已读失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 获取收件箱未读邮件数量（前端每 10 秒轮询一次，用于新邮件通知）
     * GET /api/mail/unread-count
     * <p>需要登录（JWT Token）</p>
     *
     * <p>成功响应：</p>
     * <pre>{@code
     * {
     *   "unreadCount": 3,
     *   "hasNew": true,
     *   "message": "您有 3 封未读邮件"
     * }
     * }</pre>
     */
    @GetMapping("/unread-count")
    public ResponseEntity<Map<String, Object>> getUnreadCount(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {

        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = JwtUtil.getUserIdFromToken(token);
        try {
            long count = mailService.getUnreadCount(userId);
            return ResponseEntity.ok(Map.of(
                    "unreadCount", count,
                    "hasNew", count > 0,
                    "message", count > 0
                            ? "您有 " + count + " 封未读邮件"
                            : "没有新邮件"
            ));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "查询失败: " + e.getMessage()
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
    public ResponseEntity<?> listMails(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestParam(value = "folder", defaultValue = "INBOX") String folder) {
        String token = extractBearerToken(authHeader);
        if (token == null || !JwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = JwtUtil.getUserIdFromToken(token);
        try {
            var mails = mailService.listByFolder(userId, folder);
            var data = mails.stream().map(mail -> {
                java.util.Map<String, Object> item = new java.util.HashMap<>();
                item.put("id", mail.getId());
                item.put("from", mail.getFromAddress());
                item.put("to", mail.getToAddresses());
                item.put("subject", mail.getSubject());
                item.put("receivedAt", mail.getReceivedAt() != null ? mail.getReceivedAt().toString() : null);
                item.put("isSpam", mail.getIsSpam());
                item.put("hasAttachments", mail.getHasAttachments());
                item.put("attachmentPath", mail.getAttachmentPath());
                item.put("folder", mail.getFolder().name());
                item.put("status", mail.getStatus().name());
                item.put("readFlag", mail.getReadFlag());
                // AI 分析字段（列表视图精简）
                item.put("priorityLevel", mail.getPriorityLevel());
                item.put("riskLevel", mail.getRiskLevel());
                item.put("summary", mail.getSummary());
                item.put("aiAnalyzed", mail.getAiAnalyzed());
                return item;
            }).toList();
            return ResponseEntity.ok(Map.of("mails", data));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "查询收件列表失败: " + e.getMessage()
            ));
        }
    }
}
