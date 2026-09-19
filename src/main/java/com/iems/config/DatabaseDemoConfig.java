package com.iems.config;

import org.springframework.cache.CacheManager;
import org.springframework.cache.concurrent.ConcurrentMapCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

@Configuration
@Profile("db-demo")
public class DatabaseDemoConfig {
    @Bean
    public org.springframework.boot.ApplicationRunner demoAdmin(
            com.iems.repository.UserRepository users,
            org.springframework.security.crypto.password.PasswordEncoder encoder,
            @org.springframework.beans.factory.annotation.Value("${IEMS_DEMO_ADMIN_PASSWORD}") String password) {
        return args -> {
            if (password.length() < 16) throw new IllegalArgumentException("Demo admin password must have at least 16 characters");
            if (users.count() == 0) {
                var user = new com.iems.model.entity.User();
                user.setUsername("demo-admin");
                user.setPassword(encoder.encode(password));
                user.setEmail("demo-admin@example.test");
                user.setFirstName("Demo"); user.setLastName("Administrator");
                user.setRole(com.iems.model.enums.UserRole.ADMIN);
                user.setActive(true);
                users.save(user);
            }
        };
    }

    @Bean
    public CacheManager cacheManager() {
        return new ConcurrentMapCacheManager();
    }
}
