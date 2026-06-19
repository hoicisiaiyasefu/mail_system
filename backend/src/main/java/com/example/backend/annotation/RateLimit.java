package com.example.backend.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * API 限流注解
 * 标注在 Controller 方法上，限制该接口的并发调用频率
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RateLimit {

    /** 每秒允许的请求数，默认 5 */
    double permitsPerSecond() default 5.0;

    /** 获取令牌的超时秒数，默认 0（不等待，直接拒绝） */
    long timeoutSeconds() default 0;
}
