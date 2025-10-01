package com.iems.rabbit.producer;

import com.iems.config.RabbitConfig;
import com.iems.rabbit.model.EmailTask;
import com.iems.rabbit.model.PdfTask;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Producer for sending tasks to RabbitMQ queues.
 */
@Component
public class TaskProducer {
    private static final Logger logger = LoggerFactory.getLogger(TaskProducer.class);

    @Autowired
    private RabbitTemplate rabbitTemplate;

    /**
     * Send email task to email queue.
     */
    public void sendEmailTask(EmailTask task) {
        logger.info("Sending email task to queue: {}", task.getTo());
        try {
            rabbitTemplate.convertAndSend(
                RabbitConfig.TASKS_EXCHANGE,
                RabbitConfig.EMAIL_ROUTING_KEY,
                task
            );
            logger.debug("Email task sent successfully: {}", task);
        } catch (Exception e) {
            logger.error("Failed to send email task: {}", task, e);
            throw new RuntimeException("Failed to queue email task", e);
        }
    }

    /**
     * Send PDF generation task to PDF queue.
     */
    public void sendPdfTask(PdfTask task) {
        logger.info("Sending PDF generation task to queue: {}", task.getDocumentType());
        try {
            rabbitTemplate.convertAndSend(
                RabbitConfig.TASKS_EXCHANGE,
                RabbitConfig.PDF_ROUTING_KEY,
                task
            );
            logger.debug("PDF task sent successfully: {}", task);
        } catch (Exception e) {
            logger.error("Failed to send PDF task: {}", task, e);
            throw new RuntimeException("Failed to queue PDF task", e);
        }
    }
}