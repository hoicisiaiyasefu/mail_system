package com.example.backend.controller;

import com.example.backend.service.UserService;
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

    public UserController(UserService userService) {
        this.userService = userService;
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
}
