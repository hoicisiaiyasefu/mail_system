package com.example.backend.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;

@Service
public class FileStorageService {

    /**
     * 附件存储基础路径，自动适配操作系统
     * Windows: D:/mail_storage/
     * Linux/macOS: ./mail_storage/ (项目运行目录下)
     */
    private final String basePath;

    public FileStorageService() {
        String osName = System.getProperty("os.name").toLowerCase();
        if (osName.contains("windows")) {
            this.basePath = "D:/mail_storage/";
        } else {
            // Linux/macOS：在用户目录下创建 .mail_storage 目录
            String userHome = System.getProperty("user.home");
            this.basePath = userHome + "/.mail_storage/";
        }
    }

    public String saveFile(MultipartFile file) {

        if (file == null || file.isEmpty()) {
            return null;
        }

        try {
            Path dir = Paths.get(basePath);
            if (!Files.exists(dir)) {
                Files.createDirectories(dir);
            }

            String fileName = UUID.randomUUID() + "_" + file.getOriginalFilename();
            Path target = dir.resolve(fileName);

            file.transferTo(target.toFile());

            return target.toAbsolutePath().toString();

        } catch (Exception e) {
            throw new RuntimeException("附件保存失败", e);
        }
    }
}
