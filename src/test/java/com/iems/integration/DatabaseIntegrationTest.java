package com.iems.integration;

import com.iems.model.entity.School;
import com.iems.model.entity.User;
import com.iems.model.enums.UserRole;
import com.iems.repository.SchoolRepository;
import com.iems.repository.UserRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration tests for database operations using Testcontainers.
 */
@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
@Transactional
public class DatabaseIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
            .withDatabaseName("testdb")
            .withUsername("testuser")
            .withPassword("testpass");

    @Autowired
    private SchoolRepository schoolRepository;

    @Autowired
    private UserRepository userRepository;

    @Test
    void shouldSaveAndRetrieveSchool() {
        // Given
        School school = new School();
        school.setName("Test School");
        school.setAddress("123 Test Street");
        school.setCity("Test City");
        school.setEmail("test@school.com");

        // When
        School saved = schoolRepository.save(school);
        School retrieved = schoolRepository.findById(saved.getId()).orElse(null);

        // Then
        assertNotNull(retrieved);
        assertEquals("Test School", retrieved.getName());
        assertEquals("test@school.com", retrieved.getEmail());
        assertTrue(retrieved.getActive());
    }

    @Test
    void shouldSaveUserWithSchool() {
        // Given
        School school = new School();
        school.setName("University");
        school.setEmail("info@university.edu");
        School savedSchool = schoolRepository.save(school);

        User user = new User();
        user.setUsername("testuser");
        user.setPassword("password123");
        user.setEmail("testuser@university.edu");
        user.setRole(UserRole.STUDENT);
        user.setSchool(savedSchool);

        // When
        User savedUser = userRepository.save(user);
        User retrieved = userRepository.findById(savedUser.getId()).orElse(null);

        // Then
        assertNotNull(retrieved);
        assertEquals("testuser", retrieved.getUsername());
        assertNotNull(retrieved.getSchool());
        assertEquals("University", retrieved.getSchool().getName());
    }

    @Test
    void shouldFindUserByUsername() {
        // Given
        User user = new User();
        user.setUsername("findme");
        user.setPassword("password");
        user.setEmail("findme@test.com");
        user.setRole(UserRole.TEACHER);
        userRepository.save(user);

        // When
        User found = userRepository.findByUsername("findme").orElse(null);

        // Then
        assertNotNull(found);
        assertEquals("findme@test.com", found.getEmail());
        assertEquals(UserRole.TEACHER, found.getRole());
    }

    @Test
    void shouldCheckUsernameExists() {
        // Given
        User user = new User();
        user.setUsername("existinguser");
        user.setPassword("password");
        user.setEmail("existing@test.com");
        user.setRole(UserRole.STUDENT);
        userRepository.save(user);

        // When
        boolean exists = userRepository.existsByUsername("existinguser");
        boolean notExists = userRepository.existsByUsername("nonexistent");

        // Then
        assertTrue(exists);
        assertFalse(notExists);
    }
}