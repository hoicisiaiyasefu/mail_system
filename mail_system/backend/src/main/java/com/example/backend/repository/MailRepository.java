package com.example.backend.repository;

import com.example.backend.entity.Mail;
import com.example.backend.entity.Mail.MailFolder;
import com.example.backend.entity.MailUser;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MailRepository extends JpaRepository<Mail, Long> {

    List<Mail> findByOwnerAndFolderAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
            MailUser owner, MailFolder folder);

    List<Mail> findByOwnerAndSubjectContainingAndDeletedFlagFalseOrderByCreatedAtDesc(
            MailUser owner, String subject);

    long countByOwnerAndFolderAndReadFlagFalseAndDeletedFlagFalse(MailUser owner, MailFolder folder);
}
