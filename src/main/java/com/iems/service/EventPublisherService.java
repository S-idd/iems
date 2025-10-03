package com.iems.service;

import com.iems.config.KafkaConfig;
import com.iems.kafka.model.AccessibilityEvent;
import com.iems.kafka.model.EnrollmentEvent;
import com.iems.kafka.model.ScholarshipEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

/**
 * Service for publishing events to Kafka topics.
 */
@Service
public class EventPublisherService {
    
    private static final Logger logger = LoggerFactory.getLogger(EventPublisherService.class);

    @Autowired
    private KafkaTemplate<String, Object> kafkaTemplate;

    /**
     * Publish accessibility event to Kafka.
     */
    public void publishAccessibilityEvent(AccessibilityEvent event) {
        logger.info("Publishing accessibility event: {} for school: {}", 
                    event.getEventType(), event.getSchoolId());
        
        CompletableFuture<SendResult<String, Object>> future = kafkaTemplate.send(
            KafkaConfig.ACCESSIBILITY_EVENTS_TOPIC,
            event.getSchoolId().toString(),
            event
        );

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.debug("Successfully published accessibility event: {} to partition: {}",
                           event.getId(), result.getRecordMetadata().partition());
            } else {
                logger.error("Failed to publish accessibility event: {}", event.getId(), ex);
            }
        });
    }

    /**
     * Publish scholarship event to Kafka.
     */
    public void publishScholarshipEvent(ScholarshipEvent event) {
        logger.info("Publishing scholarship event: {} for scholarship: {}", 
                    event.getEventType(), event.getScholarshipId());
        
        CompletableFuture<SendResult<String, Object>> future = kafkaTemplate.send(
            KafkaConfig.SCHOLARSHIP_EVENTS_TOPIC,
            event.getStudentId().toString(),
            event
        );

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.debug("Successfully published scholarship event: {} to partition: {}",
                           event.getScholarshipId(), result.getRecordMetadata().partition());
            } else {
                logger.error("Failed to publish scholarship event: {}", event.getScholarshipId(), ex);
            }
        });
    }

    /**
     * Publish enrollment event to Kafka.
     */
    public void publishEnrollmentEvent(EnrollmentEvent event) {
        logger.info("Publishing enrollment event: {} for enrollment: {}", 
                    event.getEventType(), event.getEnrollmentId());
        
        CompletableFuture<SendResult<String, Object>> future = kafkaTemplate.send(
            KafkaConfig.ENROLLMENT_EVENTS_TOPIC,
            event.getStudentId().toString(),
            event
        );

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.debug("Successfully published enrollment event: {} to partition: {}",
                           event.getEnrollmentId(), result.getRecordMetadata().partition());
            } else {
                logger.error("Failed to publish enrollment event: {}", event.getEnrollmentId(), ex);
            }
        });
    }

    /**
     * Publish notification event to Kafka.
     */
    public void publishNotificationEvent(String userId, String title, String message) {
        logger.info("Publishing notification event for user: {}", userId);
        
        var notificationData = new java.util.HashMap<String, Object>();
        notificationData.put("userId", userId);
        notificationData.put("title", title);
        notificationData.put("message", message);
        notificationData.put("timestamp", java.time.LocalDateTime.now());
        
        CompletableFuture<SendResult<String, Object>> future = kafkaTemplate.send(
            KafkaConfig.NOTIFICATION_EVENTS_TOPIC,
            userId,
            notificationData
        );

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.debug("Successfully published notification event to partition: {}",
                           result.getRecordMetadata().partition());
            } else {
                logger.error("Failed to publish notification event for user: {}", userId, ex);
            }
        });
    }
}