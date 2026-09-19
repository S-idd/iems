package com.iems;

import java.security.SecureRandom;
import java.util.HexFormat;
import com.ideas.contracts.starter.ContractValidationProperties;
import com.iems.dcg.validation.ScholarshipAppliedEventBoundary;
import org.springframework.beans.factory.annotation.Autowired;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

@SpringBootTest(properties = {
        "spring.flyway.enabled=false",
        "spring.jpa.hibernate.ddl-auto=create-drop",
        "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
        "spring.kafka.listener.auto-startup=false",
        "spring.rabbitmq.listener.simple.auto-startup=false",
        "spring.rabbitmq.dynamic=false",
        "contract.validation.enabled=true"})
@ActiveProfiles("db-demo")
public class IemsApplicationTests {
    @Autowired
    private ContractValidationProperties contractValidationProperties;

    @Autowired
    private ScholarshipAppliedEventBoundary scholarshipAppliedEventBoundary;
    private static final String JWT_SECRET;
    private static final String ADMIN_PASSWORD;

    static {
        byte[] secret = new byte[32];
        new SecureRandom().nextBytes(secret);
        JWT_SECRET = HexFormat.of().formatHex(secret);
        new SecureRandom().nextBytes(secret);
        ADMIN_PASSWORD = HexFormat.of().formatHex(secret);
    }

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry properties) {
        properties.add("spring.datasource.url", () -> "jdbc:h2:mem:iems_context;DB_CLOSE_DELAY=-1");
        properties.add("spring.datasource.driver-class-name", () -> "org.h2.Driver");
        properties.add("IEMS_JWT_SECRET", () -> JWT_SECRET);
        properties.add("IEMS_DEMO_ADMIN_PASSWORD", () -> ADMIN_PASSWORD);
    }

    @Test
    void contextLoads() {
        assertTrue(contractValidationProperties.isEnabled());
        assertTrue(scholarshipAppliedEventBoundary != null);
    }
}
