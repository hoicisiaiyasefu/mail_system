package com.example.backend.service;

import com.example.backend.entity.Mail;
import com.example.backend.entity.MailUser;
import com.example.backend.repository.MailRepository;
import com.example.backend.repository.MailUserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.math.BigDecimal;
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
     */
    @Transactional
    public Mail receiveMail(String fromAddress, String toAddresses,
                            String subject, String content, String contentType) {
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

        final Long mailId = savedMail.getId();
        TransactionSynchronizationManager.registerSynchronization(
                new TransactionSynchronization() {
                    @Override
                    public void afterCommit() {
                        Mail persisted = mailRepository.findById(mailId).orElse(null);
                        if (persisted != null) {
                            spamAsyncService.detectAndUpdate(persisted);
                        }
                    }
                });

        return savedMail;
    }

    public Mail findById(Long id) {
        return mailRepository.findById(id).orElse(null);
    }

    /**
     * 搜索邮件（分页）
     */
    public Page<Mail> searchByKeyword(Long userId, String keyword, int page, int size) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        return mailRepository.searchByOwnerAndKeyword(owner, keyword, PageRequest.of(page, size));
    }

    public Mail saveMail(Mail mail) {
        return mailRepository.save(mail);
    }

    /**
     * 按文件夹查询邮件列表（分页，支持 INBOX, SPAM, SENT, DRAFT, TRASH, ARCHIVE）
     */
    public Page<Mail> listByFolder(Long userId, String folderName, int page, int size) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        Mail.MailFolder folder;
        try {
            folder = Mail.MailFolder.valueOf(folderName.toUpperCase());
        } catch (IllegalArgumentException e) {
            folder = Mail.MailFolder.INBOX;
        }
        // TRASH 文件夹包含已标记 deletedFlag=true 的邮件
        if (folder == Mail.MailFolder.TRASH) {
            return mailRepository.findByOwnerAndFolder(owner, folder, PageRequest.of(page, size));
        }
        return mailRepository.findByOwnerAndFolderAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
                owner, folder, PageRequest.of(page, size));
    }

    /**
     * 发送邮件 — 创建发送副本（SENT）和接收副本（INBOX）
     *
     * @param attachmentPaths 附件的文件路径列表（逗号分隔），null 或空字符串表示无附件
     * @param bccAddresses   密送地址（逗号分隔），可为 null
     * @param inReplyToId    回复的原邮件 ID，可为 null
     */
    @Transactional
    public Map<String, Object> sendMail(Long senderUserId, String toAddresses,
                                        String subject, String content,
                                        String ccAddresses,
                                        String attachmentPaths,
                                        String bccAddresses,
                                        Long inReplyToId) {
        MailUser sender = mailUserRepository.findById(senderUserId)
                .orElseThrow(() -> new RuntimeException("发件用户不存在: id=" + senderUserId));

        boolean hasAttach = attachmentPaths != null && !attachmentPaths.isBlank();
        boolean hasBcc = bccAddresses != null && !bccAddresses.isBlank();

        // 1. 创建"已发送"副本
        Mail sentMail = new Mail();
        sentMail.setOwner(sender);
        sentMail.setSender(sender);
        sentMail.setFromAddress(sender.getEmailAddress());
        sentMail.setToAddresses(toAddresses);
        sentMail.setCcAddresses(ccAddresses);
        if (hasBcc) {
            sentMail.setBccAddresses(bccAddresses);
        }
        sentMail.setSubject(subject != null ? subject : "");
        sentMail.setContent(content != null ? content : "");
        sentMail.setContentType("text/plain");
        sentMail.setStatus(Mail.MailStatus.SENT);
        sentMail.setFolder(Mail.MailFolder.SENT);
        sentMail.setSentAt(LocalDateTime.now());
        sentMail.setReceivedAt(LocalDateTime.now());
        sentMail.setIsSpam(false);
        sentMail.setSpamScore(BigDecimal.ZERO);
        if (inReplyToId != null) {
            sentMail.setInReplyToId(inReplyToId);
        }
        if (hasAttach) {
            sentMail.setAttachmentPath(attachmentPaths);
            sentMail.setHasAttachments(true);
        }
        Mail savedSent = mailRepository.save(sentMail);
        log.info("已发送邮件副本已保存: id={}, from={}, subject={}, hasAttachment={}",
                savedSent.getId(), sender.getEmailAddress(), subject, hasAttach);

        // 2. 为每个收件人创建"收件箱"副本（含附件信息）
        String[] recipients = toAddresses.split(",");
        for (String recipientEmail : recipients) {
            String trimmed = recipientEmail.trim();
            if (trimmed.isEmpty()) continue;
            Mail received = receiveMail(
                    sender.getEmailAddress(),
                    trimmed,
                    subject,
                    content,
                    "text/plain"
            );
            // 将附件信息和回复链同步到收件人的副本
            if (hasAttach) {
                received.setAttachmentPath(attachmentPaths);
                received.setHasAttachments(true);
            }
            if (inReplyToId != null) {
                received.setInReplyToId(inReplyToId);
            }
            mailRepository.save(received);
            log.info("收件人 {} 的收件箱副本已创建: mailId={}, hasAttachment={}",
                    trimmed, received.getId(), hasAttach);
        }

        // 3. 为每个密送收件人创建"收件箱"副本（BCC 信息不写入 to/cc 列表）
        if (hasBcc) {
            String[] bccRecipients = bccAddresses.split(",");
            for (String bccEmail : bccRecipients) {
                String trimmed = bccEmail.trim();
                if (trimmed.isEmpty()) continue;
                Mail bccReceived = receiveMail(
                        sender.getEmailAddress(),
                        trimmed,
                        subject,
                        content,
                        "text/plain"
                );
                // BCC 收件人看不到 TO/CC 列表
                bccReceived.setToAddresses(trimmed);
                bccReceived.setCcAddresses(null);
                if (hasAttach) {
                    bccReceived.setAttachmentPath(attachmentPaths);
                    bccReceived.setHasAttachments(true);
                }
                if (inReplyToId != null) {
                    bccReceived.setInReplyToId(inReplyToId);
                }
                mailRepository.save(bccReceived);
                log.info("BCC 收件人 {} 的收件箱副本已创建: mailId={}", trimmed, bccReceived.getId());
            }
        }

        // 使用 HashMap（可变），控制器可能追加 attachmentPath 等字段
        java.util.HashMap<String, Object> result = new java.util.HashMap<>();
        result.put("id", savedSent.getId());
        result.put("from", sender.getEmailAddress());
        result.put("to", toAddresses);
        result.put("subject", subject);
        result.put("status", "SENT");
        result.put("message", "邮件已发送");
        return result;
    }

    // ============================================================
    // 草稿相关
    // ============================================================

    /**
     * 保存草稿
     */
    @Transactional
    public Mail saveDraft(Long userId, String to, String subject, String content, String cc) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));

        Mail draft = new Mail();
        draft.setOwner(owner);
        draft.setFromAddress(owner.getEmailAddress());
        draft.setToAddresses(to != null ? to : "");
        draft.setCcAddresses(cc != null ? cc : "");
        draft.setSubject(subject != null ? subject : "");
        draft.setContent(content != null ? content : "");
        draft.setContentType("text/plain");
        draft.setStatus(Mail.MailStatus.DRAFT);
        draft.setFolder(Mail.MailFolder.DRAFT);
        draft.setReceivedAt(LocalDateTime.now());
        draft.setSentAt(LocalDateTime.now());
        draft.setIsSpam(false);
        draft.setSpamScore(BigDecimal.ZERO);

        Mail saved = mailRepository.save(draft);
        log.info("草稿已保存: id={}, subject={}", saved.getId(), subject);
        return saved;
    }

    /**
     * 更新草稿
     */
    @Transactional
    public Mail updateDraft(Long draftId, Long userId, String to, String subject, String content, String cc) {
        Mail draft = mailRepository.findById(draftId)
                .orElseThrow(() -> new RuntimeException("草稿不存在: id=" + draftId));
        if (!draft.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该草稿");
        }
        if (draft.getFolder() != Mail.MailFolder.DRAFT) {
            throw new RuntimeException("该邮件不是草稿");
        }

        draft.setToAddresses(to != null ? to : draft.getToAddresses());
        draft.setCcAddresses(cc != null ? cc : draft.getCcAddresses());
        draft.setSubject(subject != null ? subject : draft.getSubject());
        draft.setContent(content != null ? content : draft.getContent());
        draft.setSentAt(LocalDateTime.now());

        Mail saved = mailRepository.save(draft);
        log.info("草稿已更新: id={}", draftId);
        return saved;
    }

    /**
     * 删除草稿（硬删除）
     */
    @Transactional
    public void deleteDraft(Long draftId, Long userId) {
        Mail draft = mailRepository.findById(draftId)
                .orElseThrow(() -> new RuntimeException("草稿不存在: id=" + draftId));
        if (!draft.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该草稿");
        }
        mailRepository.delete(draft);
        log.info("草稿已删除: id={}", draftId);
    }

    // ============================================================
    // B模块（基础功能扩展）：删除、标记已读、未读通知
    // ============================================================

    @Transactional
    public void softDelete(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mail.setDeletedFlag(true);
        mail.setFolder(Mail.MailFolder.TRASH);
        mailRepository.save(mail);
        log.info("邮件已删除: id={}, subject={}", mailId, mail.getSubject());
    }

    /**
     * 彻底删除邮件（硬删除）
     */
    @Transactional
    public void permanentDelete(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mailRepository.delete(mail);
        log.info("邮件已彻底删除: id={}", mailId);
    }

    /**
     * 清空废纸篓（彻底删除 TRASH 文件夹中的所有邮件）
     * @return 删除的邮件数
     */
    @Transactional
    public long emptyTrash(Long userId) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        var trashMails = mailRepository.findByOwnerAndFolder(
                owner, Mail.MailFolder.TRASH, PageRequest.of(0, Integer.MAX_VALUE));
        long count = trashMails.getTotalElements();
        if (count > 0) {
            mailRepository.deleteAll(trashMails.getContent());
        }
        log.info("废纸篓已清空，共删除 {} 封邮件", count);
        return count;
    }

    @Transactional
    public void markAsRead(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mail.setReadFlag(true);
        mailRepository.save(mail);
        log.info("邮件已标记为已读: id={}", mailId);
    }

    /**
     * 标记邮件为非垃圾邮件（移回收件箱）
     */
    @Transactional
    public void markAsNotSpam(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mail.setIsSpam(false);
        mail.setSpamScore(BigDecimal.ZERO);
        mail.setFolder(Mail.MailFolder.INBOX);
        mailRepository.save(mail);
        log.info("邮件已标记为非垃圾邮件: id={}", mailId);
    }

    /**
     * 批量标记为已读
     */
    @Transactional
    public int batchMarkAsRead(List<Long> mailIds, Long userId) {
        int count = 0;
        for (Long mailId : mailIds) {
            Mail mail = mailRepository.findById(mailId).orElse(null);
            if (mail != null && mail.getOwner().getId().equals(userId)) {
                mail.setReadFlag(true);
                mailRepository.save(mail);
                count++;
            }
        }
        return count;
    }

    /**
     * 批量软删除
     */
    @Transactional
    public int batchSoftDelete(List<Long> mailIds, Long userId) {
        int count = 0;
        for (Long mailId : mailIds) {
            Mail mail = mailRepository.findById(mailId).orElse(null);
            if (mail != null && mail.getOwner().getId().equals(userId)) {
                mail.setDeletedFlag(true);
                mail.setFolder(Mail.MailFolder.TRASH);
                mailRepository.save(mail);
                count++;
            }
        }
        log.info("批量删除 {} 封邮件", count);
        return count;
    }

    public long getUnreadCount(Long userId) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        return mailRepository.countByOwnerAndFolderAndReadFlagFalseAndDeletedFlagFalse(
                owner, Mail.MailFolder.INBOX);
    }

    // ============================================================
    // C模块：已读/未读切换、标星、归档、移动
    // ============================================================

    /**
     * 切换已读/未读状态
     */
    @Transactional
    public void toggleRead(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mail.setReadFlag(!mail.getReadFlag());
        mailRepository.save(mail);
        log.info("邮件已读状态切换: id={}, readFlag={}", mailId, mail.getReadFlag());
    }

    /**
     * 切换标星/取消标星
     */
    @Transactional
    public void toggleStar(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mail.setStarredFlag(!mail.getStarredFlag());
        mailRepository.save(mail);
        log.info("邮件标星状态切换: id={}, starred={}", mailId, mail.getStarredFlag());
    }

    /**
     * 归档邮件
     */
    @Transactional
    public void archive(Long mailId, Long userId) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        mail.setFolder(Mail.MailFolder.ARCHIVE);
        mailRepository.save(mail);
        log.info("邮件已归档: id={}", mailId);
    }

    /**
     * 移动邮件到指定文件夹
     */
    @Transactional
    public void moveToFolder(Long mailId, Long userId, String folderName) {
        Mail mail = mailRepository.findById(mailId)
                .orElseThrow(() -> new RuntimeException("邮件不存在: id=" + mailId));
        if (!mail.getOwner().getId().equals(userId)) {
            throw new RuntimeException("无权操作该邮件");
        }
        try {
            Mail.MailFolder targetFolder = Mail.MailFolder.valueOf(folderName.toUpperCase());
            mail.setFolder(targetFolder);
            mailRepository.save(mail);
            log.info("邮件已移动到: id={}, folder={}", mailId, targetFolder);
        } catch (IllegalArgumentException e) {
            throw new RuntimeException("无效的文件夹: " + folderName);
        }
    }

    /**
     * 按标星过滤查询（分页）
     */
    public Page<Mail> listStarred(Long userId, int page, int size) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        return mailRepository.findByOwnerAndStarredFlagTrueAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
                owner, PageRequest.of(page, size));
    }

    /**
     * 增强搜索：支持按文件夹、发件人筛选（分页）
     */
    public Page<Mail> searchAdvanced(Long userId, String keyword, String folder, String from, int page, int size) {
        MailUser owner = mailUserRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在: id=" + userId));
        String kw = (keyword != null && !keyword.isBlank()) ? keyword.trim() : null;
        String fr = (from != null && !from.isBlank()) ? from.trim() : null;

        // 如果指定了文件夹
        if (folder != null && !folder.isBlank()) {
            try {
                Mail.MailFolder mailFolder = Mail.MailFolder.valueOf(folder.toUpperCase());
                return mailRepository.searchByOwnerAndFolderAndKeyword(
                        owner, mailFolder, kw, fr, PageRequest.of(page, size));
            } catch (IllegalArgumentException e) {
                // 无效文件夹名，回退到全局搜索
            }
        }
        // 全局搜索
        return mailRepository.searchByOwnerAndKeywordAdvanced(
                owner, kw, fr, PageRequest.of(page, size));
    }

    // ============================================================
    // 私有辅助方法
    // ============================================================

    private String extractFirstEmail(String toAddresses) {
        if (toAddresses == null || toAddresses.isBlank()) {
            return "unknown@example.com";
        }
        String[] parts = toAddresses.split(",");
        return parts[0].trim();
    }

    private MailUser findOrCreateUser(String email) {
        return mailUserRepository.findByEmailAddress(email)
                .orElseGet(() -> {
                    MailUser newUser = new MailUser();
                    newUser.setEmailAddress(email);
                    String baseUsername = email.split("@")[0];
                    String username = baseUsername;
                    int suffix = 1;
                    while (mailUserRepository.existsByUsername(username)) {
                        username = baseUsername + suffix;
                        suffix++;
                    }
                    newUser.setUsername(username);
                    newUser.setPasswordHash("");
                    return mailUserRepository.save(newUser);
                });
    }
}
