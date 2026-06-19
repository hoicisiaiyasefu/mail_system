package com.example.backend.repository;

import com.example.backend.entity.Contact;
import com.example.backend.entity.MailUser;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ContactRepository extends JpaRepository<Contact, Long> {

    List<Contact> findByOwnerOrderByNameAsc(MailUser owner);

    List<Contact> findByOwnerAndNameContainingOrOwnerAndEmailAddressContainingOrderByNameAsc(
            MailUser owner1, String name, MailUser owner2, String email);

    boolean existsByOwnerAndEmailAddress(MailUser owner, String emailAddress);
}
