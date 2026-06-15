package com.example.backend.controller;

import com.example.backend.entity.Contact;
import com.example.backend.entity.MailUser;
import com.example.backend.repository.ContactRepository;
import com.example.backend.repository.MailUserRepository;
import com.example.backend.util.JwtUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/contacts")
@CrossOrigin(origins = "*")
public class ContactController {

    private final ContactRepository contactRepository;
    private final MailUserRepository userRepository;
    private final JwtUtil jwtUtil;

    public ContactController(ContactRepository contactRepository,
                            MailUserRepository userRepository,
                            JwtUtil jwtUtil) {
        this.contactRepository = contactRepository;
        this.userRepository = userRepository;
        this.jwtUtil = jwtUtil;
    }

    /**
     * 获取联系人列表
     * GET /api/contacts
     */
    @GetMapping
    public ResponseEntity<?> listContacts(
            @RequestHeader(value = "Authorization", required = false) String authHeader) {
        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of("error", "未登录"));
        }
        Long userId = jwtUtil.getUserIdFromToken(token);
        MailUser owner = userRepository.findById(userId).orElse(null);
        if (owner == null) return ResponseEntity.status(404).body(Map.of("error", "用户不存在"));

        List<Contact> contacts = contactRepository.findByOwnerOrderByNameAsc(owner);
        var data = contacts.stream().map(c -> Map.<String, Object>of(
                "id", c.getId(),
                "name", c.getName(),
                "email", c.getEmailAddress(),
                "phone", c.getPhone() != null ? c.getPhone() : "",
                "groupName", c.getGroupName() != null ? c.getGroupName() : "",
                "notes", c.getNotes() != null ? c.getNotes() : ""
        )).collect(Collectors.toList());

        return ResponseEntity.ok(Map.of("contacts", data));
    }

    /**
     * 新增联系人
     * POST /api/contacts
     */
    @PostMapping
    public ResponseEntity<?> addContact(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @RequestBody Map<String, Object> body) {
        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of("error", "未登录"));
        }
        Long userId = jwtUtil.getUserIdFromToken(token);
        MailUser owner = userRepository.findById(userId).orElse(null);
        if (owner == null) return ResponseEntity.status(404).body(Map.of("error", "用户不存在"));

        String name = (String) body.get("name");
        String email = (String) body.get("email");
        if (name == null || name.isBlank() || email == null || email.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "姓名和邮箱不能为空"));
        }

        Contact contact = new Contact();
        contact.setOwner(owner);
        contact.setName(name);
        contact.setEmailAddress(email);
        contact.setPhone((String) body.getOrDefault("phone", ""));
        contact.setGroupName((String) body.getOrDefault("groupName", ""));
        contact.setNotes((String) body.getOrDefault("notes", ""));
        contactRepository.save(contact);

        return ResponseEntity.ok(Map.of("id", contact.getId(), "message", "联系人已添加"));
    }

    /**
     * 更新联系人
     * PUT /api/contacts/{id}
     */
    @PutMapping("/{id}")
    public ResponseEntity<?> updateContact(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @PathVariable Long id,
            @RequestBody Map<String, Object> body) {
        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of("error", "未登录"));
        }
        Long userId = jwtUtil.getUserIdFromToken(token);

        Contact contact = contactRepository.findById(id).orElse(null);
        if (contact == null || !contact.getOwner().getId().equals(userId)) {
            return ResponseEntity.status(404).body(Map.of("error", "联系人不存在或无权操作"));
        }

        if (body.containsKey("name")) contact.setName((String) body.get("name"));
        if (body.containsKey("email")) contact.setEmailAddress((String) body.get("email"));
        if (body.containsKey("phone")) contact.setPhone((String) body.get("phone"));
        if (body.containsKey("groupName")) contact.setGroupName((String) body.get("groupName"));
        if (body.containsKey("notes")) contact.setNotes((String) body.get("notes"));
        contactRepository.save(contact);

        return ResponseEntity.ok(Map.of("message", "联系人已更新"));
    }

    /**
     * 删除联系人
     * DELETE /api/contacts/{id}
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteContact(
            @RequestHeader(value = "Authorization", required = false) String authHeader,
            @PathVariable Long id) {
        String token = extractBearerToken(authHeader);
        if (token == null || !jwtUtil.validateToken(token)) {
            return ResponseEntity.status(401).body(Map.of("error", "未登录"));
        }
        Long userId = jwtUtil.getUserIdFromToken(token);

        Contact contact = contactRepository.findById(id).orElse(null);
        if (contact == null || !contact.getOwner().getId().equals(userId)) {
            return ResponseEntity.status(404).body(Map.of("error", "联系人不存在或无权操作"));
        }

        contactRepository.delete(contact);
        return ResponseEntity.ok(Map.of("message", "联系人已删除"));
    }

    private String extractBearerToken(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        return null;
    }
}
