package com.iems.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.ExchangeBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * RabbitMQ configuration for command processing and async tasks.
 * Defines exchanges, queues, and bindings for email delivery and PDF generation.
 */
@Configuration
public class RabbitConfig {

    // Exchange names
    public static final String TASKS_EXCHANGE = "iems.tasks.exchange";
    public static final String DLX_EXCHANGE = "iems.tasks.dlx";

    // Queue names
    public static final String EMAIL_QUEUE = "iems.tasks.email";
    public static final String PDF_QUEUE = "iems.tasks.pdf";
    public static final String EMAIL_DLQ = "iems.tasks.email.dlq";
    public static final String PDF_DLQ = "iems.tasks.pdf.dlq";

    // Routing keys
    public static final String EMAIL_ROUTING_KEY = "task.email";
    public static final String PDF_ROUTING_KEY = "task.pdf";

    /**
     * Tasks exchange for distributing async commands.
     */
    @Bean
    public TopicExchange tasksExchange() {
        return ExchangeBuilder
                .topicExchange(TASKS_EXCHANGE)
                .durable(true)
                .build();
    }

    /**
     * Dead Letter Exchange for failed messages.
     */
    @Bean
    public DirectExchange deadLetterExchange() {
        return ExchangeBuilder
                .directExchange(DLX_EXCHANGE)
                .durable(true)
                .build();
    }

    /**
     * Email task queue with DLX configuration.
     */
    @Bean
    public Queue emailQueue() {
        return QueueBuilder
                .durable(EMAIL_QUEUE)
                .withArgument("x-dead-letter-exchange", DLX_EXCHANGE)
                .withArgument("x-dead-letter-routing-key", "email.dlq")
                .withArgument("x-message-ttl", 3600000) // 1 hour TTL
                .build();
    }

    /**
     * Email dead letter queue.
     */
    @Bean
    public Queue emailDeadLetterQueue() {
        return QueueBuilder
                .durable(EMAIL_DLQ)
                .build();
    }

    /**
     * PDF generation task queue with DLX configuration.
     */
    @Bean
    public Queue pdfQueue() {
        return QueueBuilder
                .durable(PDF_QUEUE)
                .withArgument("x-dead-letter-exchange", DLX_EXCHANGE)
                .withArgument("x-dead-letter-routing-key", "pdf.dlq")
                .withArgument("x-message-ttl", 3600000) // 1 hour TTL
                .build();
    }

    /**
     * PDF generation dead letter queue.
     */
    @Bean
    public Queue pdfDeadLetterQueue() {
        return QueueBuilder
                .durable(PDF_DLQ)
                .build();
    }

    /**
     * Bind email queue to tasks exchange.
     */
    @Bean
    public Binding emailBinding(Queue emailQueue, TopicExchange tasksExchange) {
        return BindingBuilder
                .bind(emailQueue)
                .to(tasksExchange)
                .with(EMAIL_ROUTING_KEY);
    }

    /**
     * Bind PDF queue to tasks exchange.
     */
    @Bean
    public Binding pdfBinding(Queue pdfQueue, TopicExchange tasksExchange) {
        return BindingBuilder
                .bind(pdfQueue)
                .to(tasksExchange)
                .with(PDF_ROUTING_KEY);
    }

    /**
     * Bind email DLQ to dead letter exchange.
     */
    @Bean
    public Binding emailDlqBinding(Queue emailDeadLetterQueue, DirectExchange deadLetterExchange) {
        return BindingBuilder
                .bind(emailDeadLetterQueue)
                .to(deadLetterExchange)
                .with("email.dlq");
    }

    /**
     * Bind PDF DLQ to dead letter exchange.
     */
    @Bean
    public Binding pdfDlqBinding(Queue pdfDeadLetterQueue, DirectExchange deadLetterExchange) {
        return BindingBuilder
                .bind(pdfDeadLetterQueue)
                .to(deadLetterExchange)
                .with("pdf.dlq");
    }

    /**
     * Message converter for JSON serialization.
     */
    @Bean
    public MessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    /**
     * RabbitMQ template with JSON converter.
     */
    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(messageConverter());
        return template;
    }

    /**
     * Listener container factory with JSON converter.
     */
    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(messageConverter());
        factory.setConcurrentConsumers(3);
        factory.setMaxConcurrentConsumers(10);
        factory.setPrefetchCount(10);
        return factory;
    }
}