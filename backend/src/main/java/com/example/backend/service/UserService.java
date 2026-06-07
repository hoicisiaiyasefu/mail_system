package com.example.backend.service;

import com.example.backend.entity.MailUser;
import com.example.backend.repository.MailUserRepository;
import com.example.backend.util.JwtUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.Optional;

/**
 * 用户业务服务 — 注册、登录、密码加密
 */
@Service
public class UserService {

    private static final Logger log = LoggerFactory.getLogger(UserService.class);
    private static final String PASSWORD_SALT = "mail-system-salt-2026";

    private final MailUserRepository userRepository;

    public UserService(MailUserRepository userRepository) {
        this.userRepository = userRepository;
    }

    // ============================================================
    // 注册
    // ============================================================

    /**
     * 用户注册
     *
     * @param username 用户名（登录用）
     * @param password 明文密码
     * @param email    邮箱地址
     * @return 结果 Map（成功含 user 信息，失败含 error）
     */
    @Transactional
    public Map<String, Object> register(String username, String password, String email) {
        // 校验用户名唯一性
        if (userRepository.existsByUsername(username)) {
            return Map.of("error", "用户名已存在");
        }
        // 校验邮箱唯一性
        if (userRepository.existsByEmailAddress(email)) {
            return Map.of("error", "邮箱已被注册");
        }

        MailUser user = new MailUser();
        user.setUsername(username);
        user.setEmailAddress(email);
        user.setPasswordHash(hashPassword(password));
        user.setNickname(username);          // 默认昵称 = 用户名
        user.setStatus(MailUser.UserStatus.ACTIVE);

        MailUser saved = userRepository.save(user);
        log.info("新用户注册成功: id={}, username={}, email={}", saved.getId(), username, email);

        return Map.of(
                "message", "注册成功",
                "user", Map.of(
                        "id", saved.getId(),
                        "username", saved.getUsername(),
                        "email", saved.getEmailAddress()
                )
        );
    }

    // ============================================================
    // 登录
    // ============================================================

    /**
     * 用户登录 — 校验密码，返回 JWT Token
     *
     * @param username 用户名
     * @param password 明文密码
     * @return 结果 Map（成功含 token + user，失败含 error）
     */
    @Transactional
    public Map<String, Object> login(String username, String password) {
        Optional<MailUser> optUser = userRepository.findByUsername(username);
        if (optUser.isEmpty()) {
            return Map.of("error", "用户名或密码错误");
        }

        MailUser user = optUser.get();

        // 校验密码
        if (!verifyPassword(password, user.getPasswordHash())) {
            return Map.of("error", "用户名或密码错误");
        }

        // 校验账号状态
        if (user.getStatus() != MailUser.UserStatus.ACTIVE) {
            return Map.of("error", "账号已被禁用，请联系管理员");
        }

        // 更新最后登录时间
        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);

        // 生成 JWT Token
        String token = JwtUtil.generateToken(user.getId(), user.getUsername());
        log.info("用户登录成功: id={}, username={}", user.getId(), username);

        return Map.of(
                "message", "登录成功",
                "token", token,
                "user", Map.of(
                        "id", user.getId(),
                        "username", user.getUsername(),
                        "email", user.getEmailAddress()
                )
        );
    }

    // ============================================================
    // 密码加密（SHA-256 + 固定盐值）
    // ============================================================

    /**
     * 对明文密码做 SHA-256 哈希
     */
    private String hashPassword(String password) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            String salted = password + PASSWORD_SALT;
            byte[] hash = md.digest(salted.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("密码加密算法不可用", e);
        }
    }

    /**
     * 校验明文密码是否与存储的哈希值匹配
     */
    private boolean verifyPassword(String rawPassword, String storedHash) {
        return hashPassword(rawPassword).equals(storedHash);
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
