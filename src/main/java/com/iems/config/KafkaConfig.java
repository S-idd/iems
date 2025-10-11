package com.iems.config;

import java.util.HashMap;
import java.util.Map;

import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.ErrorHandlingDeserializer;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;

import com.iems.kafka.model.AccessibilityEvent;

/**
 * Kafka configuration for event-driven communication.
 * Defines topics, producers, and consumers for the IEMS event streaming architecture.
 */
@EnableKafka
@Configuration
public class KafkaConfig {

    @Value("${spring.kafka.bootstrap-servers}")
    private String bootstrapServers;

    @Value("${spring.kafka.consumer.group-id}")
    private String consumerGroupId;

    // Topic names
    public static final String ACCESSIBILITY_EVENTS_TOPIC = "iems.events.accessibility";
    public static final String SCHOLARSHIP_EVENTS_TOPIC = "iems.events.scholarship";
    public static final String ENROLLMENT_EVENTS_TOPIC = "iems.events.enrollment";
    public static final String NOTIFICATION_EVENTS_TOPIC = "iems.events.notification";
    public static final String METRICS_TOPIC = "iems.metrics";

    /**
     * Kafka Admin configuration for managing topics and clusters.
     */
    @Bean
    public KafkaAdmin kafkaAdmin() {
        Map<String, Object> configs = new HashMap<>();
        configs.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        return new KafkaAdmin(configs);
    }

    /**
     * Create Accessibility Events Topic.
     */
    @Bean
    public NewTopic accessibilityEventsTopic() {
        return TopicBuilder.name(ACCESSIBILITY_EVENTS_TOPIC)
                .partitions(3)
                .replicas(1)
                .config("retention.ms", "604800000") // 7 days
                .config("compression.type", "snappy")
                .build();
    }

    /**
     * Create Scholarship Events Topic.
     */
    @Bean
    public NewTopic scholarshipEventsTopic() {
        return TopicBuilder.name(SCHOLARSHIP_EVENTS_TOPIC)
                .partitions(3)
                .replicas(1)
                .config("retention.ms", "604800000") // 7 days
                .config("compression.type", "snappy")
                .build();
    }

    /**
     * Create Enrollment Events Topic.
     */
    @Bean
    public NewTopic enrollmentEventsTopic() {
        return TopicBuilder.name(ENROLLMENT_EVENTS_TOPIC)
                .partitions(3)
                .replicas(1)
                .config("retention.ms", "604800000") // 7 days
                .config("compression.type", "snappy")
                .build();
    }

    /**
     * Create Notification Events Topic.
     */
    @Bean
    public NewTopic notificationEventsTopic() {
        return TopicBuilder.name(NOTIFICATION_EVENTS_TOPIC)
                .partitions(3)
                .replicas(1)
                .config("retention.ms", "259200000") // 3 days
                .config("compression.type", "snappy")
                .build();
    }

    /**
     * Create Metrics Topic for aggregated analytics.
     */
    @Bean
    public NewTopic metricsTopic() {
        return TopicBuilder.name(METRICS_TOPIC)
                .partitions(2)
                .replicas(1)
                .config("retention.ms", "2592000000") // 30 days
                .config("compression.type", "snappy")
                .build();
    }

    /**
     * Producer configuration for sending events to Kafka.
     */
    @Bean
    public ProducerFactory<String, Object> producerFactory() {
        Map<String, Object> configProps = new HashMap<>();
        configProps.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        configProps.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        configProps.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        configProps.put(ProducerConfig.ACKS_CONFIG, "all");
        configProps.put(ProducerConfig.RETRIES_CONFIG, 3);
        configProps.put(ProducerConfig.LINGER_MS_CONFIG, 10);
        configProps.put(ProducerConfig.BATCH_SIZE_CONFIG, 16384);
        configProps.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");
        configProps.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        configProps.put(JsonSerializer.ADD_TYPE_INFO_HEADERS, false);
        
        return new DefaultKafkaProducerFactory<>(configProps);
    }

    /**
     * Kafka template for producing messages.
     */
    @Bean
    public KafkaTemplate<String, Object> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }

    @Bean
    public KafkaTemplate<String, AccessibilityEvent> accessibilityKafkaTemplate() {
        return new KafkaTemplate<>(new DefaultKafkaProducerFactory<>(producerFactory().getConfigurationProperties()));

    }


    /**
     * Consumer configuration for receiving events from Kafka.
     */
    @Bean
    public ConsumerFactory<String, Object> consumerFactory() {
        Map<String, Object> configProps = new HashMap<>();
        configProps.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        configProps.put(ConsumerConfig.GROUP_ID_CONFIG, consumerGroupId);
        configProps.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        configProps.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        configProps.put(ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS, StringDeserializer.class);
        configProps.put(ErrorHandlingDeserializer.VALUE_DESERIALIZER_CLASS, JsonDeserializer.class);
        configProps.put(JsonDeserializer.TRUSTED_PACKAGES, "com.iems.kafka.model");
        configProps.put(JsonDeserializer.USE_TYPE_INFO_HEADERS, false);
        configProps.put(JsonDeserializer.VALUE_DEFAULT_TYPE, "com.iems.kafka.model.AccessibilityEvent");
        configProps.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        configProps.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);
        configProps.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 100);
        
        return new DefaultKafkaConsumerFactory<>(configProps);
    }

    /**
     * Container factory for Kafka listeners.
     */
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory() {
        ConcurrentKafkaListenerContainerFactory<String, Object> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory());
        factory.setConcurrency(3);
        factory.getContainerProperties().setPollTimeout(3000);
        return factory;
    }
}