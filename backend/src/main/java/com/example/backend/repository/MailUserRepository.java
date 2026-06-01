package com.example.backend.repository;

import com.example.backend.entity.MailUser;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MailUserRepository extends JpaRepository<MailUser, Long> {

    Optional<MailUser> findByUsername(String username);

    Optional<MailUser> findByEmailAddress(String emailAddress);

    boolean existsByUsername(String username);

    boolean existsByEmailAddress(String emailAddress);
}
