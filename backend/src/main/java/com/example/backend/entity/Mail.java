package com.example.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.ForeignKey;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "mail")
public class Mail {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(
            name = "owner_id",
            nullable = false,
            foreignKey = @ForeignKey(name = "fk_mail_owner"))
    private MailUser owner;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sender_id", foreignKey = @ForeignKey(name = "fk_mail_sender"))
    private MailUser sender;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "recipient_id", foreignKey = @ForeignKey(name = "fk_mail_recipient"))
    private MailUser recipient;

    @Column(name = "from_address", nullable = false, length = 120)
    private String fromAddress;

    @Column(name = "to_addresses", nullable = false, columnDefinition = "text")
    private String toAddresses;

    @Column(name = "cc_addresses", columnDefinition = "text")
    private String ccAddresses;

    @Column(name = "bcc_addresses", columnDefinition = "text")
    private String bccAddresses;

    @Column(nullable = false, length = 200)
    private String subject;

    @Lob
    @Column(nullable = false, columnDefinition = "longtext")
    private String content;

    @Column(name = "content_type", nullable = false, length = 30)
    private String contentType = "text/plain";

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private MailFolder folder = MailFolder.INBOX;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private MailStatus status = MailStatus.RECEIVED;

    @Column(name = "read_flag", nullable = false)
    private Boolean readFlag = false;

    @Column(name = "starred_flag", nullable = false)
    private Boolean starredFlag = false;

    @Column(name = "deleted_flag", nullable = false)
    private Boolean deletedFlag = false;

    @Column(name = "has_attachments", nullable = false)
    private Boolean hasAttachments = false;

    @Column(name = "attachment_info", columnDefinition = "text")
    private String attachmentInfo;

    @Column(name = "spam_score", precision = 5, scale = 4)
    private BigDecimal spamScore;

    @Column(name = "is_spam", nullable = false)
    private Boolean isSpam = false;

    @Column(name = "sent_at")
    private LocalDateTime sentAt;

    @Column(name = "received_at")
    private LocalDateTime receivedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        createdAt = now;
        updatedAt = now;
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public enum MailFolder {
        INBOX,
        SENT,
        DRAFT,
        TRASH,
        SPAM,
        ARCHIVE
    }

    public enum MailStatus {
        DRAFT,
        SENT,
        RECEIVED,
        FAILED
    }
}
