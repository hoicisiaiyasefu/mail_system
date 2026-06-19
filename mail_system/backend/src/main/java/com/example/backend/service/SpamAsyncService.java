package com.example.backend.service;

import com.example.backend.ai.SpamDetectorService;
import com.example.backend.entity.Mail;
import com.example.backend.repository.MailRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;

/**
 * 异步垃圾邮件检测服务 - 独立服务确保 @Async 通过 AOP 代理生效
 */
@Service
public class SpamAsyncService {

    private static final Logger log = LoggerFactory.getLogger(SpamAsyncService.class);

    private final MailRepository mailRepository;
    private final SpamDetectorService spamDetectorService;

    public SpamAsyncService(MailRepository mailRepository,
                            SpamDetectorService spamDetectorService) {
        this.mailRepository = mailRepository;
        this.spamDetectorService = spamDetectorService;
    }

    /**
     * 异步调用 Python ML 垃圾邮件检测模块，并将结果回写到数据库
     */
    @Async
    @Transactional
    public void detectAndUpdate(Mail mail) {
        try {
            log.info("开始异步垃圾邮件检测: mailId={}", mail.getId());

            Map<String, Object> result = spamDetectorService.detect(
                    mail.getId(),
                    mail.getFromAddress(),
                    mail.getToAddresses(),
                    mail.getSubject(),
                    mail.getContent()
            );

            if (result.containsKey("error")) {
                log.warn("垃圾邮件检测失败: mailId={}, error={}", mail.getId(), result.get("error"));
                return;
            }

            boolean isSpam = Boolean.TRUE.equals(result.get("is_spam"));
            double spamScore = 0.0;
            Object scoreObj = result.get("spam_score");
            if (scoreObj instanceof Number) {
                spamScore = ((Number) scoreObj).doubleValue();
            }

            // 回写到数据库
            Mail latest = mailRepository.findById(mail.getId()).orElse(null);
            if (latest != null) {
                latest.setIsSpam(isSpam);
                latest.setSpamScore(BigDecimal.valueOf(spamScore).setScale(4, RoundingMode.HALF_UP));
                if (isSpam) {
                    latest.setFolder(Mail.MailFolder.SPAM);
                }
                mailRepository.save(latest);
                log.info("垃圾邮件检测完成: mailId={}, isSpam={}, score={}",
                        mail.getId(), isSpam, spamScore);
            }

        } catch (Exception e) {
            log.error("异步垃圾邮件检测异常: mailId={}, error={}", mail.getId(), e.getMessage(), e);
        }
    }
}