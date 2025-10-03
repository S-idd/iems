package com.iems.rabbit.listener;

import com.iems.config.RabbitConfig;
import com.iems.rabbit.model.EmailTask;
import com.iems.service.EmailService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Listener for processing email tasks from RabbitMQ.
 */
@Component
public class EmailTaskListener {
    private static final Logger logger = LoggerFactory.getLogger(EmailTaskListener.class);

    @Autowired
    private EmailService emailService;

    @RabbitListener(queues = RabbitConfig.EMAIL_QUEUE)
    public void handleEmailTask(EmailTask task) {
        logger.info("Received email task for: {}", task.getTo());
        try {
            emailService.sendEmail(task.getTo(), task.getSubject(), task.getBody(), task.isHtml());
            logger.info("Email sent successfully to: {}", task.getTo());
        } catch (Exception e) {
            logger.error("Failed to send email to: {}", task.getTo(), e);
            throw e; // Will retry or send to DLQ
        }
    }
}