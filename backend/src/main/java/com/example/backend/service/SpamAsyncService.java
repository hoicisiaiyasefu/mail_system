package com.example.backend.service;

import com.example.backend.ai.PriorityEngineService;
import com.example.backend.ai.SecurityEngineService;
import com.example.backend.ai.SpamDetectorService;
import com.example.backend.ai.SummaryService;
import com.example.backend.entity.Mail;
import com.example.backend.repository.MailRepository;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * AI 异步综合分析服务
 * 使用独立线程池异步执行 AI 分析管道，不阻塞邮件接收响应
 */
@Service
public class SpamAsyncService {

    private static final Logger log = LoggerFactory.getLogger(SpamAsyncService.class);

    private final MailRepository mailRepository;
    private final SpamDetectorService spamDetectorService;
    private final SecurityEngineService securityEngineService;
    private final PriorityEngineService priorityEngineService;
    private final SummaryService summaryService;

    private ExecutorService executor;

    public SpamAsyncService(MailRepository mailRepository,
                            SpamDetectorService spamDetectorService,
                            SecurityEngineService securityEngineService,
                            PriorityEngineService priorityEngineService,
                            SummaryService summaryService) {
        this.mailRepository = mailRepository;
        this.spamDetectorService = spamDetectorService;
        this.securityEngineService = securityEngineService;
        this.priorityEngineService = priorityEngineService;
        this.summaryService = summaryService;
    }

    @PostConstruct
    void init() {
        executor = new ThreadPoolExecutor(
                2, 5, 60L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(20),
                r -> {
                    Thread t = new Thread(r, "ai-analysis");
                    t.setDaemon(true);
                    return t;
                });
        log.info("AI 分析线程池已初始化: corePool=2, maxPool=5");
    }

    @PreDestroy
    void destroy() {
        if (executor != null) {
            executor.shutdown();
            try {
                executor.awaitTermination(30, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }

    /**
     * 异步执行完整的 AI 分析管道
     */
    public void detectAndUpdate(Mail mail) {
        final Long mailId = mail.getId();
        executor.submit(() -> {
            log.info("=== 开始 AI 综合分析管道: mailId={} ===", mailId);
            try {
                runAnalysisPipeline(mailId);
            } catch (Exception e) {
                log.error("AI 综合分析管道异常: mailId={}, error={}", mailId, e.getMessage(), e);
            }
        });
    }

    /**
     * AI 分析管道主逻辑（同步执行，由线程池调用）
     */
    @Transactional
    void runAnalysisPipeline(Long mailId) {
        Mail latest = mailRepository.findById(mailId).orElse(null);
        if (latest == null) {
            log.warn("邮件不存在，跳过 AI 分析: mailId={}", mailId);
            return;
        }

        String from = latest.getFromAddress();
        String to = latest.getToAddresses();
        String subject = latest.getSubject();
        String content = latest.getContent();
        // 用收件人地址作为 currentUser（避免触发 owner 的懒加载）
        String firstRecipient = to != null ? to.split(",")[0].trim() : "";
        String currentUser = !firstRecipient.isEmpty() ? firstRecipient : from;

        // 第1步：垃圾邮件检测 (ML + LLM)
        runSpamDetection(latest, from, to, subject, content);

        // 第2步：安全威胁分析
        runSecurityAnalysis(latest, from, to, subject, content);

        // 第3步：优先级排序
        runPriorityScoring(latest, from, to, subject, content, currentUser);

        // 第4步：邮件摘要生成
        runSummaryGeneration(latest, from, subject, content);

        // 标记完成
        latest.setAiAnalyzed(true);
        mailRepository.save(latest);

        log.info("=== AI 综合分析管道完成: mailId={}, isSpam={}, riskLevel={}, priorityLevel={} ===",
                latest.getId(), latest.getIsSpam(),
                latest.getRiskLevel(), latest.getPriorityLevel());
    }

    private void runSpamDetection(Mail mail, String from, String to,
                                   String subject, String content) {
        try {
            log.debug("  第1步: 垃圾邮件检测... mailId={}", mail.getId());
            Map<String, Object> result = spamDetectorService.detect(
                    mail.getId(), from, to, subject, content);

            if (result.containsKey("error")) {
                log.warn("  垃圾邮件检测失败: mailId={}, error={}", mail.getId(), result.get("error"));
                return;
            }

            boolean isSpam = Boolean.TRUE.equals(result.get("is_spam"));
            double spamScore = getDoubleValue(result, "spam_score");

            mail.setIsSpam(isSpam);
            mail.setSpamScore(toDecimal(spamScore));
            if (isSpam) {
                mail.setFolder(Mail.MailFolder.SPAM);
            }

            String method = (String) result.getOrDefault("method", "ML");
            log.info("  垃圾邮件检测完成: mailId={}, isSpam={}, score={}, method={}",
                    mail.getId(), isSpam, spamScore, method);

        } catch (Exception e) {
            log.error("  垃圾邮件检测异常: mailId={}, error={}", mail.getId(), e.getMessage());
        }
    }

    private void runSecurityAnalysis(Mail mail, String from, String to,
                                      String subject, String content) {
        try {
            log.debug("  第2步: 安全威胁分析... mailId={}", mail.getId());
            Map<String, Object> result = securityEngineService.analyze(
                    mail.getId(), from, to, subject, content, null, null);

            if (result.containsKey("error")) {
                log.warn("  安全分析失败: mailId={}, error={}", mail.getId(), result.get("error"));
                return;
            }

            String riskLevel = (String) result.getOrDefault("risk_level", "safe");
            double riskScore = getDoubleValue(result, "risk_score");

            mail.setRiskLevel(riskLevel);
            mail.setRiskScore(toDecimal(riskScore));

            log.info("  安全分析完成: mailId={}, riskLevel={}, riskScore={}",
                    mail.getId(), riskLevel, riskScore);

        } catch (Exception e) {
            log.error("  安全分析异常: mailId={}, error={}", mail.getId(), e.getMessage());
        }
    }

    private void runPriorityScoring(Mail mail, String from, String to,
                                     String subject, String content, String currentUser) {
        try {
            log.debug("  第3步: 优先级排序... mailId={}", mail.getId());
            Map<String, Object> result = priorityEngineService.score(
                    mail.getId(), from, to, subject, content, currentUser);

            if (result.containsKey("error")) {
                log.warn("  优先级排序失败: mailId={}, error={}", mail.getId(), result.get("error"));
                return;
            }

            double priorityScore = getDoubleValue(result, "priority_score");
            String priorityLevel = (String) result.getOrDefault("priority_level", "normal");

            mail.setPriorityScore(toDecimal(priorityScore));
            mail.setPriorityLevel(priorityLevel);

            log.info("  优先级排序完成: mailId={}, priorityLevel={}, priorityScore={}",
                    mail.getId(), priorityLevel, priorityScore);

        } catch (Exception e) {
            log.error("  优先级排序异常: mailId={}, error={}", mail.getId(), e.getMessage());
        }
    }

    private void runSummaryGeneration(Mail mail, String from,
                                       String subject, String content) {
        try {
            log.debug("  第4步: 邮件摘要生成... mailId={}", mail.getId());
            Map<String, Object> result = summaryService.summarize(
                    mail.getId(), from, subject, content);

            if (result.containsKey("error")) {
                log.warn("  摘要生成失败: mailId={}, error={}", mail.getId(), result.get("error"));
                return;
            }

            String summary = (String) result.getOrDefault("summary", "");
            String method = (String) result.getOrDefault("method", "extractive");

            if (summary != null && !summary.isBlank()) {
                mail.setSummary(summary);
            }

            log.info("  摘要生成完成: mailId={}, method={}, length={}",
                    mail.getId(), method, summary != null ? summary.length() : 0);

        } catch (Exception e) {
            log.error("  摘要生成异常: mailId={}, error={}", mail.getId(), e.getMessage());
        }
    }

    private double getDoubleValue(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof Number) {
            return ((Number) value).doubleValue();
        }
        return 0.0;
    }

    private BigDecimal toDecimal(double value) {
        return BigDecimal.valueOf(value).setScale(4, RoundingMode.HALF_UP);
    }
}
