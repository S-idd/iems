package com.iems.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import com.iems.kafka.model.AccessibilityEvent;
import com.iems.kafka.model.ScholarshipEvent;

/**
 * Minimal event publisher service used by other services to publish domain events.
 * This is intentionally lightweight: it logs events and publishes to Kafka when a
 * KafkaTemplate bean is available.
 */
@Service
public class EventPublisherService {

    private static final Logger logger = LoggerFactory.getLogger(EventPublisherService.class);

    @Autowired(required = false)
    private KafkaTemplate<String, Object> kafkaTemplate;

    public void publishAccessibilityEvent(AccessibilityEvent event) {
        logger.debug("Publishing accessibility event: {}", event);
        if (kafkaTemplate != null) {
            kafkaTemplate.send("accessibility-events", event);
        }
    }

    public void publishScholarshipEvent(ScholarshipEvent event) {
        logger.debug("Publishing scholarship event: {}", event);
        if (kafkaTemplate != null) {
            kafkaTemplate.send("scholarship-events", event);
        }
    }
}
