package com.iems;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * Main application class for the Inclusive Education Management System (IEMS).
 * 
 * This system provides comprehensive management capabilities for educational institutions
 * with focus on inclusivity, accessibility, and scholarship management.
 * 
 * Key features:
 * - Multi-role authentication and authorization
 * - Student and scholarship management
 * - Accessibility reporting and accommodations
 * - Event-driven architecture with Kafka and RabbitMQ
 * - Real-time metrics and monitoring
 * 
 * @author IEMS Team
 * @version 1.0.0
 * @since 2024-01-01
 */
@SpringBootApplication
@EnableCaching
@EnableKafka
@EnableAsync
@EnableScheduling
@EnableTransactionManagement
public class IemsApplication {

    /**
     * Main entry point for the IEMS application.
     * 
     * @param args command line arguments
     */
    public static void main(String[] args) {
        SpringApplication.run(IemsApplication.class, args);
    }
}