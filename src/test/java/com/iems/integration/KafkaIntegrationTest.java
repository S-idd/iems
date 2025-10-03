package com.iems.integration;

import com.iems.config.KafkaConfig;
import com.iems.kafka.model.AccessibilityEvent;
import com.iems.kafka.producer.EventProducer;
import com.iems.model.enums.DisabilityType;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration tests for Kafka event publishing and consumption.
 */
@SpringBootTest
@ActiveProfiles("test")
@EmbeddedKafka(partitions = 1, topics = {KafkaConfig.ACCESSIBILITY_EVENTS_TOPIC})
public class KafkaIntegrationTest {

    @Autowired
    private EventProducer eventProducer;

    private CountDownLatch latch = new CountDownLatch(1);
    private AccessibilityEvent receivedEvent;

    @Test
    void shouldPublishAndConsumeAccessibilityEvent() throws InterruptedException {
        // Given
        AccessibilityEvent event = new AccessibilityEvent();
        event.setId(1L);
        event.setSchoolId(1L);
        event.setSchoolName("Test School");
        event.setStudentId(1L);
        event.setStudentName("John Doe");
        event.setEventType("REPORT_CREATED");
        event.setDisabilityType(DisabilityType.VISUAL);
        event.setSeverity("HIGH");

        // When
        eventProducer.publishAccessibilityEvent(event);

        // Then
        boolean messageReceived = latch.await(10, TimeUnit.SECONDS);
        assertTrue(messageReceived);
        assertNotNull(receivedEvent);
        assertEquals("REPORT_CREATED", receivedEvent.getEventType());
        assertEquals(DisabilityType.VISUAL, receivedEvent.getDisabilityType());
    }

    @KafkaListener(topics = KafkaConfig.ACCESSIBILITY_EVENTS_TOPIC, groupId = "test-group")
    public void listen(ConsumerRecord<String, AccessibilityEvent> record) {
        receivedEvent = record.value();
        latch.countDown();
    }
}