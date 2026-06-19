package com.example.backend.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 工具类 — Token 生成、校验、用户信息提取
 */
public class JwtUtil {

    // 签名密钥（至少 256 bits = 32 bytes，当前 47 bytes 满足要求）
    private static final String SECRET = "mail-system-jwt-secret-key-2026-super-secure-!!";
    // Token 有效期：24 小时
    private static final long EXPIRATION_MS = 24 * 60 * 60 * 1000;

    private static SecretKey getKey() {
        byte[] keyBytes = SECRET.getBytes(StandardCharsets.UTF_8);
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
    public static String generateToken(Long userId, String username) {
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
    public static Claims parseToken(String token) {
        return Jwts.parser()
                .verifyWith(getKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * 校验 Token 是否有效（未过期、签名正确）
     */
    public static boolean validateToken(String token) {
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
    public static Long getUserIdFromToken(String token) {
        Claims claims = parseToken(token);
        return claims.get("userId", Long.class);
    }

    /**
     * 从 Token 中提取用户名
     */
    public static String getUsernameFromToken(String token) {
        return parseToken(token).getSubject();
    }
}
