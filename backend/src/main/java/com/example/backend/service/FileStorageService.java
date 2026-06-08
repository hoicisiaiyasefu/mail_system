package com.example.backend.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.util.UUID;

@Service
public class FileStorageService {

    private final String basePath = "D:/mail_storage/";

    public String saveFile(MultipartFile file) {

        if (file == null || file.isEmpty()) {
            return null;
        }

        try {
            File dir = new File(basePath);
            if (!dir.exists()) {
                dir.mkdirs();
            }

            String fileName =
                    UUID.randomUUID() + "_" + file.getOriginalFilename();

            File target = new File(basePath + fileName);

            file.transferTo(target);

            return target.getAbsolutePath();

        } catch (Exception e) {
            throw new RuntimeException("附件保存失败", e);
        }
    }
}