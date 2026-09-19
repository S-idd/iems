package com.iems.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.iems.model.entity.User;
import com.iems.model.enums.UserRole;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsername(String username);
    Optional<User> findByEmail(String email);
    Boolean existsByUsername(String username);
    Boolean existsByEmail(String email);
    List<User> findByRole(UserRole role);
    List<User> findBySchoolIdAndActive(Long schoolId, Boolean active);
    
    Optional<User> findByRefreshToken(String token);
}
