package com.example.backend.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 工具类 — Token 生成、校验、用户信息提取
 * <p>密钥通过 application.yml 中的 jwt.secret 配置，支持环境变量覆盖</p>
 */
@Component
public class JwtUtil {

    private String secret;

    // Token 有效期：24 小时
    private static final long EXPIRATION_MS = 24 * 60 * 60 * 1000;

    @Value("${jwt.secret}")
    public void setSecret(String secret) {
        this.secret = secret;
    }

    private SecretKey getKey() {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        return Keys.hmacShaKeyFor(keyBytes);
    }

    // ============================================================
    // Token 生成
    // ============================================================

    /**
     * 根据用户信息生成 JWT Token
     *
     * @param userId   用户 ID
     * @param username 用户名
     * @return JWT 字符串
     */
    public String generateToken(Long userId, String username) {
        Date now = new Date();
        return Jwts.builder()
                .subject(username)
                .claim("userId", userId)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + EXPIRATION_MS))
                .signWith(getKey())
                .compact();
    }

    // ============================================================
    // Token 校验与解析
    // ============================================================

    /**
     * 解析 Token，返回其中的 Claims
     */
    public Claims parseToken(String token) {
        return Jwts.parser()
                .verifyWith(getKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * 校验 Token 是否有效（未过期、签名正确）
     */
    public boolean validateToken(String token) {
        try {
            parseToken(token);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 从 Token 中提取用户 ID
     */
    public Long getUserIdFromToken(String token) {
        Claims claims = parseToken(token);
        return claims.get("userId", Long.class);
    }

    /**
     * 从 Token 中提取用户名
     */
    public String getUsernameFromToken(String token) {
        return parseToken(token).getSubject();
    }
}
