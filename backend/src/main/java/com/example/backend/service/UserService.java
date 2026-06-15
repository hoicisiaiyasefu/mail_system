package com.example.backend.service;

import com.example.backend.entity.MailUser;
import com.example.backend.repository.MailUserRepository;
import com.example.backend.util.JwtUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
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
 * <p>密码使用 BCrypt 加密，兼容旧的 SHA-256 密码（自动升级）</p>
 */
@Service
public class UserService {

    private static final Logger log = LoggerFactory.getLogger(UserService.class);
    /** @deprecated 仅用于兼容旧密码，新密码使用 BCrypt */
    @Deprecated
    private static final String PASSWORD_SALT = "mail-system-salt-2026";

    private final MailUserRepository userRepository;
    private final JwtUtil jwtUtil;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public UserService(MailUserRepository userRepository, JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.jwtUtil = jwtUtil;
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
        user.setPasswordHash(passwordEncoder.encode(password));
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
     * <p>兼容旧 SHA-256 密码，登录时自动升级为 BCrypt</p>
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

        // 校验密码（优先 BCrypt，兼容旧 SHA-256）
        boolean passwordOk = false;
        String storedHash = user.getPasswordHash();
        if (storedHash != null && storedHash.startsWith("$2a$")) {
            // BCrypt 格式
            passwordOk = passwordEncoder.matches(password, storedHash);
        } else {
            // 旧 SHA-256 格式 — 兼容校验后自动升级
            passwordOk = verifyLegacyPassword(password, storedHash);
            if (passwordOk) {
                user.setPasswordHash(passwordEncoder.encode(password));
                log.info("用户 {} 密码已从 SHA-256 自动升级为 BCrypt", username);
            }
        }

        if (!passwordOk) {
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
        String token = jwtUtil.generateToken(user.getId(), user.getUsername());
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
    // 用户设置
    // ============================================================

    public Map<String, Object> getProfile(Long userId) {
        MailUser user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        return Map.of(
                "id", user.getId(),
                "username", user.getUsername(),
                "email", user.getEmailAddress(),
                "nickname", user.getNickname() != null ? user.getNickname() : user.getUsername(),
                "signature", user.getSignature() != null ? user.getSignature() : ""
        );
    }

    @Transactional
    public void updateProfile(Long userId, String nickname) {
        MailUser user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        if (nickname != null && !nickname.isBlank()) {
            user.setNickname(nickname);
            userRepository.save(user);
            log.info("用户 {} 昵称已更新", user.getUsername());
        }
    }

    @Transactional
    public void changePassword(Long userId, String oldPassword, String newPassword) {
        MailUser user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        // 验证旧密码
        boolean oldOk = false;
        String storedHash = user.getPasswordHash();
        if (storedHash != null && storedHash.startsWith("$2a$")) {
            oldOk = passwordEncoder.matches(oldPassword, storedHash);
        } else {
            oldOk = verifyLegacyPassword(oldPassword, storedHash);
        }
        if (!oldOk) {
            throw new RuntimeException("旧密码不正确");
        }

        user.setPasswordHash(passwordEncoder.encode(newPassword));
        userRepository.save(user);
        log.info("用户 {} 密码已修改", user.getUsername());
    }

    @Transactional
    public void updateSignature(Long userId, String signature) {
        MailUser user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        user.setSignature(signature);
        userRepository.save(user);
        log.info("用户 {} 签名已更新", user.getUsername());
    }

    // ============================================================
    // 密码加密（BCrypt，兼容旧 SHA-256）
    // ============================================================

    /**
     * 旧版 SHA-256 哈希校验（仅用于兼容已存在的密码）
     * @deprecated 仅兼容迁移用，新密码统一使用 BCrypt
     */
    @Deprecated
    private boolean verifyLegacyPassword(String rawPassword, String storedHash) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            String salted = rawPassword + PASSWORD_SALT;
            byte[] hash = md.digest(salted.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(hash).equals(storedHash);
        } catch (NoSuchAlgorithmException e) {
            return false;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
