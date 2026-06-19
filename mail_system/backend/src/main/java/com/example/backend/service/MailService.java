package com.example.backend.service;

import com.example.backend.ai.SpamDetectorService;
import com.example.backend.entity.Mail;
import com.example.backend.entity.MailUser;
import com.example.backend.repository.MailRepository;
import com.example.backend.repository.MailUserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 邮件业务服务 - 处理邮件接收、存储与 AI 自动打标签
 */
@Service
public class MailService {

    private static final Logger log = LoggerFactory.getLogger(MailService.class);

    private final MailRepository mailRepository;
    private final MailUserRepository mailUserRepository;
    private final SpamAsyncService spamAsyncService;

    public MailService(MailRepository mailRepository,
                       MailUserRepository mailUserRepository,
                       SpamAsyncService spamAsyncService) {
        this.mailRepository = mailRepository;
        this.mailUserRepository = mailUserRepository;
        this.spamAsyncService = spamAsyncService;
    }

    /**
     * 接收新邮件：保存到数据库，并异步触发垃圾邮件检测
     *
     * @param fromAddress 发件人地址
     * @param toAddresses 收件人地址（逗号分隔）
     * @param subject     主题
     * @param content     正文
     * @param contentType 内容类型
     * @return 已保存的 Mail 实体
     */
    @Transactional
    public Mail receiveMail(String fromAddress, String toAddresses,
                            String subject, String content, String contentType) {
        // 查找或创建 owner（以第一个收件人为 owner）
        String ownerEmail = extractFirstEmail(toAddresses);
        MailUser owner = findOrCreateUser(ownerEmail);

        Mail mail = new Mail();
        mail.setOwner(owner);
        mail.setFromAddress(fromAddress);
        mail.setToAddresses(toAddresses);
        mail.setSubject(subject != null ? subject : "");
        mail.setContent(content != null ? content : "");
        mail.setContentType(contentType != null ? contentType : "text/plain");
        mail.setStatus(Mail.MailStatus.RECEIVED);
        mail.setFolder(Mail.MailFolder.INBOX);
        mail.setReceivedAt(LocalDateTime.now());
        mail.setSentAt(LocalDateTime.now());
        mail.setIsSpam(false);
        mail.setSpamScore(BigDecimal.ZERO);

        Mail savedMail = mailRepository.save(mail);
        log.info("新邮件已保存: id={}, from={}, subject={}", savedMail.getId(), fromAddress, subject);

        // 异步触发 AI 垃圾邮件检测（委托 SpamAsyncService 确保 @Async 代理生效）
        spamAsyncService.detectAndUpdate(savedMail);

        return savedMail;
    }

    /**
     * 根据邮件ID查询
     */
    public Mail findById(Long id) {
        return mailRepository.findById(id).orElse(null);
    }

    public Mail saveMail(Mail mail) {
        return mailRepository.save(mail);
    }

    public List<Mail> listInboxByUserId(Long userId) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        return mailRepository.findByOwnerAndFolderAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
                owner, Mail.MailFolder.INBOX);
    }

    /**
     * 查询用户的垃圾邮件列表
     */
    public List<Mail> findSpamByOwner(MailUser owner) {
        return mailRepository.findByOwnerAndFolderAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
                owner, Mail.MailFolder.SPAM);
    }

    /**
     * 发送邮件 — 创建发送副本（SENT）和接收副本（INBOX）
     *
     * @param senderUserId 发件人用户 ID（从 JWT Token 中提取）
     * @param toAddresses  收件人地址（多个用逗号分隔）
     * @param subject      主题
     * @param content      正文
     * @param ccAddresses  抄送地址（可选）
     * @return 结果 Map（含发送邮件信息）
     */
    @Transactional
    public Map<String, Object> sendMail(Long senderUserId, String toAddresses,
                                        String subject, String content,
                                        String ccAddresses) {
        // 查找发件人
        MailUser sender = mailUserRepository.findById(senderUserId)
                .orElseThrow(() -> new RuntimeException("发件用户不存在: id=" + senderUserId));

        // 1. 创建"已发送"副本（发件人视角）
        Mail sentMail = new Mail();
        sentMail.setOwner(sender);
        sentMail.setSender(sender);
        sentMail.setFromAddress(sender.getEmailAddress());
        sentMail.setToAddresses(toAddresses);
        sentMail.setCcAddresses(ccAddresses);
        sentMail.setSubject(subject != null ? subject : "");
        sentMail.setContent(content != null ? content : "");
        sentMail.setContentType("text/plain");
        sentMail.setStatus(Mail.MailStatus.SENT);
        sentMail.setFolder(Mail.MailFolder.SENT);
        sentMail.setSentAt(LocalDateTime.now());
        sentMail.setReceivedAt(LocalDateTime.now());
        sentMail.setIsSpam(false);
        sentMail.setSpamScore(BigDecimal.ZERO);
        Mail savedSent = mailRepository.save(sentMail);
        log.info("已发送邮件副本已保存: id={}, from={}, subject={}",
                savedSent.getId(), sender.getEmailAddress(), subject);

        // 2. 为每个收件人创建"收件箱"副本（接收方视角），并触发垃圾邮件检测
        String[] recipients = toAddresses.split(",");
        for (String recipientEmail : recipients) {
            String trimmed = recipientEmail.trim();
            if (trimmed.isEmpty()) {
                continue;
            }
            // 复用 receiveMail 逻辑（含异步垃圾邮件检测）
            Mail received = receiveMail(
                    sender.getEmailAddress(),
                    trimmed,
                    subject,
                    content,
                    "text/plain"
            );
            log.info("收件人 {} 的收件箱副本已创建: mailId={}", trimmed, received.getId());
        }

        return Map.of(
                "id", savedSent.getId(),
                "from", sender.getEmailAddress(),
                "to", toAddresses,
                "subject", subject,
                "status", "SENT",
                "message", "邮件已发送"
        );
    }

    // ============================================================
    // 私有辅助方法
    // ============================================================

    private String extractFirstEmail(String toAddresses) {
        if (toAddresses == null || toAddresses.isBlank()) {
            return "unknown@example.com";
        }
        // 取第一个逗号分隔的地址
        String[] parts = toAddresses.split(",");
        return parts[0].trim();
    }

    private MailUser findOrCreateUser(String email) {
        return mailUserRepository.findByEmailAddress(email)
                .orElseGet(() -> {
                    MailUser newUser = new MailUser();
                    newUser.setEmailAddress(email);
                    newUser.setUsername(email.split("@")[0]);
                    newUser.setPasswordHash(""); // 系统内部用户，无密码
                    return mailUserRepository.save(newUser);
                });
    }
}