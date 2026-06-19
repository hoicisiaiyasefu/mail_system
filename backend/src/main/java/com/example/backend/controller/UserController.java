package com.example.backend.controller;

import com.example.backend.annotation.RateLimit;
import com.example.backend.service.UserService;
import com.example.backend.util.JwtUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 用户接口 — 注册与登录
 *
 * <p>所有接口返回 JSON 格式：成功时不含 "error" 键，失败时含 "error" 键。</p>
 */
@RestController
@RequestMapping("/api/user")
@CrossOrigin(origins = "*")
public class UserController {

    private final UserService userService;
    private final JwtUtil jwtUtil;

    public UserController(UserService userService, JwtUtil jwtUtil) {
        this.userService = userService;
        this.jwtUtil = jwtUtil;
    }

    /**
     * 用户注册
     * POST /api/user/register
     *
     * <p>请求体 JSON：</p>
     * <pre>{@code
     * {
     *   "username": "zhangsan",
     *   "password": "123456",
     *   "email": "zhangsan@example.com"
     * }
     * }</pre>
     *
     * <p>成功响应：</p>
     * <pre>{@code
     * {
     *   "message": "注册成功",
     *   "user": { "id": 1, "username": "zhangsan", "email": "zhangsan@example.com" }
     * }
     * }</pre>
     */
    @RateLimit(permitsPerSecond = 3)
    @PostMapping("/register")
    public ResponseEntity<Map<String, Object>> register(@RequestBody Map<String, Object> body) {
        String username = (String) body.get("username");
        String password = (String) body.get("password");
        String email    = (String) body.get("email");

        // 参数校验
        if (username == null || username.isBlank() ||
            password == null || password.isBlank() ||
            email    == null || email.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "用户名、密码和邮箱不能为空"
            ));
        }

        if (password.length() < 6) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "密码长度不能少于 6 位"
            ));
        }

        Map<String, Object> result = userService.register(username, password, email);
        if (result.containsKey("error")) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    /**
     * 用户登录
     * POST /api/user/login
     *
     * <p>请求体 JSON：</p>
     * <pre>{@code
     * {
     *   "username": "zhangsan",
     *   "password": "123456"
     * }
     * }</pre>
     *
     * <p>成功响应：</p>
     * <pre>{@code
     * {
     *   "message": "登录成功",
     *   "token": "eyJhbGciOiJIUzI1NiJ9...",
     *   "user": { "id": 1, "username": "zhangsan", "email": "zhangsan@example.com" }
     * }
     * }</pre>
     */
    @RateLimit(permitsPerSecond = 5)
    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody Map<String, Object> body) {
        String username = (String) body.get("username");
        String password = (String) body.get("password");

        if (username == null || username.isBlank() ||
            password == null || password.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "用户名和密码不能为空"
            ));
        }

        Map<String, Object> result = userService.login(username, password);
        if (result.containsKey("error")) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    // ============================================================
    // 用户设置
    // ============================================================

    /**
     * 获取用户资料
     * GET /api/user/profile
     */
    @GetMapping("/profile")
    public ResponseEntity<Map<String, Object>> getProfile(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {

        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = jwtUtil.getUserIdFromToken(token);
        Map<String, Object> profile = userService.getProfile(userId);
        return ResponseEntity.ok(profile);
    }

    /**
     * 修改昵称
     * PUT /api/user/profile
     */
    @PutMapping("/profile")
    public ResponseEntity<Map<String, Object>> updateProfile(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestBody Map<String, Object> body) {

        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = jwtUtil.getUserIdFromToken(token);
        String nickname = (String) body.get("nickname");
        try {
            userService.updateProfile(userId, nickname);
            return ResponseEntity.ok(Map.of("message", "资料已更新"));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "更新失败: " + e.getMessage()
            ));
        }
    }

    /**
     * 修改密码
     * PUT /api/user/password
     */
    @PutMapping("/password")
    public ResponseEntity<Map<String, Object>> changePassword(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestBody Map<String, Object> body) {

        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = jwtUtil.getUserIdFromToken(token);
        String oldPassword = (String) body.get("oldPassword");
        String newPassword = (String) body.get("newPassword");

        if (oldPassword == null || oldPassword.isBlank() || newPassword == null || newPassword.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "旧密码和新密码不能为空"
            ));
        }
        if (newPassword.length() < 6) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "新密码长度不能少于 6 位"
            ));
        }

        try {
            userService.changePassword(userId, oldPassword, newPassword);
            return ResponseEntity.ok(Map.of("message", "密码已修改"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", e.getMessage()
            ));
        }
    }

    /**
     * 修改邮件签名
     * PUT /api/user/signature
     */
    @PutMapping("/signature")
    public ResponseEntity<Map<String, Object>> updateSignature(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestBody Map<String, Object> body) {

        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of(
                    "error", "未登录或 Token 已过期，请重新登录"
            ));
        }

        Long userId = jwtUtil.getUserIdFromToken(token);
        String signature = (String) body.get("signature");
        try {
            userService.updateSignature(userId, signature);
            return ResponseEntity.ok(Map.of("message", "签名已更新"));
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                    "error", "更新失败: " + e.getMessage()
            ));
        }
    }

    private String extractBearerToken(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        return null;
    }
}
