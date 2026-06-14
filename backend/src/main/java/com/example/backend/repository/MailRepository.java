package com.example.backend.repository;

import com.example.backend.entity.Mail;
import com.example.backend.entity.Mail.MailFolder;
import com.example.backend.entity.MailUser;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MailRepository extends JpaRepository<Mail, Long> {

    List<Mail> findByOwnerAndFolderAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
            MailUser owner, MailFolder folder);

    List<Mail> findByOwnerAndSubjectContainingAndDeletedFlagFalseOrderByCreatedAtDesc(
            MailUser owner, String subject);

    @Query("select m from Mail m where m.owner = :owner and m.deletedFlag = false "
            + "and (lower(m.subject) like lower(concat('%', :keyword, '%')) "
            + "or lower(m.content) like lower(concat('%', :keyword, '%'))) "
            + "order by m.receivedAt desc, m.createdAt desc")
    List<Mail> searchByOwnerAndKeyword(@Param("owner") MailUser owner,
                                       @Param("keyword") String keyword);

    long countByOwnerAndFolderAndReadFlagFalseAndDeletedFlagFalse(MailUser owner, MailFolder folder);
}
