package com.iems.kafka.producer;

import com.iems.config.KafkaConfig;
import com.iems.kafka.model.AccessibilityEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

/**
 * Kafka producer for publishing accessibility events.
 */
@Component
public class EventProducer {

    private static final Logger LOG = LoggerFactory.getLogger(EventProducer.class);

    private final KafkaTemplate<String, AccessibilityEvent> kafkaTemplate;

    @Autowired
    public EventProducer(KafkaTemplate<String, AccessibilityEvent> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    /**
     * Publishes an AccessibilityEvent to the Kafka topic.
     *
     * @param event the AccessibilityEvent to publish
     */
    public void publishAccessibilityEvent(AccessibilityEvent event) {
        try {
            kafkaTemplate.send(KafkaConfig.ACCESSIBILITY_EVENTS_TOPIC, event.getId().toString(), event);
            LOG.info("Published event with ID {} to topic {}", event.getId(), KafkaConfig.ACCESSIBILITY_EVENTS_TOPIC);
        } catch (Exception e) {
            LOG.error("Failed to publish event with ID {}: {}", event.getId(), e.getMessage(), e);
            throw new RuntimeException("Failed to publish event", e);
        }
    }
}