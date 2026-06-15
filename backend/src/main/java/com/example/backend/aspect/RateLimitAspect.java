package com.example.backend.aspect;

import com.example.backend.annotation.RateLimit;
import com.google.common.util.concurrent.RateLimiter;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * API 限流切面
 * 为标注了 @RateLimit 的方法提供 Guava RateLimiter 限流保护
 */
@Aspect
@Component
public class RateLimitAspect {

    private static final Logger log = LoggerFactory.getLogger(RateLimitAspect.class);

    private final ConcurrentHashMap<String, RateLimiter> limiters = new ConcurrentHashMap<>();

    @Around("@annotation(com.example.backend.annotation.RateLimit)")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();
        RateLimit annotation = method.getAnnotation(RateLimit.class);

        String key = method.getDeclaringClass().getSimpleName() + "." + method.getName();
        RateLimiter limiter = limiters.computeIfAbsent(key,
                k -> RateLimiter.create(annotation.permitsPerSecond()));

        if (annotation.timeoutSeconds() > 0) {
            // 等待获取令牌
            if (!limiter.tryAcquire(annotation.timeoutSeconds(), java.util.concurrent.TimeUnit.SECONDS)) {
                log.warn("API 限流触发: {}", key);
                return ResponseEntity.status(429).body(Map.of(
                        "error", "请求过于频繁，请稍后再试"
                ));
            }
        } else {
            // 不等待，立即判断
            if (!limiter.tryAcquire()) {
                log.warn("API 限流触发: {}", key);
                return ResponseEntity.status(429).body(Map.of(
                        "error", "请求过于频繁，请稍后再试"
                ));
            }
        }

        return joinPoint.proceed();
    }
}
