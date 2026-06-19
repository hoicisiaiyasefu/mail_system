package com.example.backend.repository;

import com.example.backend.entity.Mail;
import com.example.backend.entity.Mail.MailFolder;
import com.example.backend.entity.MailUser;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MailRepository extends JpaRepository<Mail, Long> {

    Page<Mail> findByOwnerAndFolderAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
            MailUser owner, MailFolder folder, Pageable pageable);

    Page<Mail> findByOwnerAndSubjectContainingAndDeletedFlagFalseOrderByCreatedAtDesc(
            MailUser owner, String subject, Pageable pageable);

    @Query("select m from Mail m where m.owner = :owner and m.deletedFlag = false "
            + "and (lower(m.subject) like lower(concat('%', :keyword, '%')) "
            + "or lower(cast(m.content as string)) like lower(concat('%', :keyword, '%'))) "
            + "order by m.receivedAt desc, m.createdAt desc")
    Page<Mail> searchByOwnerAndKeyword(@Param("owner") MailUser owner,
                                       @Param("keyword") String keyword,
                                       Pageable pageable);

    long countByOwnerAndFolderAndReadFlagFalseAndDeletedFlagFalse(MailUser owner, MailFolder folder);

    Page<Mail> findByOwnerAndFolder(MailUser owner, MailFolder folder, Pageable pageable);

    // 标星邮件查询
    Page<Mail> findByOwnerAndStarredFlagTrueAndDeletedFlagFalseOrderByReceivedAtDescCreatedAtDesc(
            MailUser owner, Pageable pageable);

    // 增强搜索：按文件夹 + 关键字 + 发件人
    @Query("select m from Mail m where m.owner = :owner and m.deletedFlag = false "
            + "and (:folder is null or m.folder = :folder) "
            + "and (:keyword is null or lower(m.subject) like lower(concat('%', :keyword, '%')) "
            + "or lower(cast(m.content as string)) like lower(concat('%', :keyword, '%'))) "
            + "and (:from is null or lower(m.fromAddress) like lower(concat('%', :from, '%'))) "
            + "order by m.receivedAt desc, m.createdAt desc")
    Page<Mail> searchByOwnerAndFolderAndKeyword(
            @Param("owner") MailUser owner,
            @Param("folder") Mail.MailFolder folder,
            @Param("keyword") String keyword,
            @Param("from") String from,
            Pageable pageable);

    // 全局搜索（不限制文件夹）+ 发件人筛选
    @Query("select m from Mail m where m.owner = :owner and m.deletedFlag = false "
            + "and (:keyword is null or lower(m.subject) like lower(concat('%', :keyword, '%')) "
            + "or lower(cast(m.content as string)) like lower(concat('%', :keyword, '%'))) "
            + "and (:from is null or lower(m.fromAddress) like lower(concat('%', :from, '%'))) "
            + "order by m.receivedAt desc, m.createdAt desc")
    Page<Mail> searchByOwnerAndKeywordAdvanced(
            @Param("owner") MailUser owner,
            @Param("keyword") String keyword,
            @Param("from") String from,
            Pageable pageable);
}
