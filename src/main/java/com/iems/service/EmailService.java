package com.iems.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

import jakarta.mail.internet.MimeMessage;

/**
 * Service for sending emails.
 */
@Service
public class EmailService {
    private static final Logger logger = LoggerFactory.getLogger(EmailService.class);

    @Autowired
    private JavaMailSender mailSender;

    @Value("${app.notification.email.from:noreply@iems.com}")
    private String fromEmail;

    @Value("${app.notification.email.enabled:true}")
    private boolean emailEnabled;

    /**
     * Send email with plain text or HTML content.
     */
    public void sendEmail(String to, String subject, String body, boolean isHtml) {
        if (!emailEnabled) {
            logger.info("Email sending is disabled. Skipping email to: {}", to);
            return;
        }

        try {
            if (isHtml) {
                MimeMessage message = mailSender.createMimeMessage();
                MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
                helper.setFrom(fromEmail);
                helper.setTo(to);
                helper.setSubject(subject);
                helper.setText(body, true);
                mailSender.send(message);
            } else {
                SimpleMailMessage message = new SimpleMailMessage();
                message.setFrom(fromEmail);
                message.setTo(to);
                message.setSubject(subject);
                message.setText(body);
                mailSender.send(message);
            }
            logger.info("Email sent successfully to: {}", to);
        } catch (Exception e) {
            logger.error("Failed to send email to: {}", to, e);
            throw new RuntimeException("Failed to send email", e);
        }
    }

    /**
     * Send simple text email.
     */
    public void sendSimpleEmail(String to, String subject, String body) {
        sendEmail(to, subject, body, false);
    }

    /**
     * Send HTML email.
     */
    public void sendHtmlEmail(String to, String subject, String htmlBody) {
        sendEmail(to, subject, htmlBody, true);
    }

    /**
     * Send email with CC and BCC.
     */
    public void sendEmailWithCopy(String to, String cc, String bcc, String subject, String body) {
        if (!emailEnabled) {
            logger.info("Email sending is disabled. Skipping email to: {}", to);
            return;
        }

        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(fromEmail);
            helper.setTo(to);
            if (cc != null && !cc.isEmpty()) {
                helper.setCc(cc);
            }
            if (bcc != null && !bcc.isEmpty()) {
                helper.setBcc(bcc);
            }
            helper.setSubject(subject);
            helper.setText(body, true);
            mailSender.send(message);
            logger.info("Email with copy sent successfully to: {}", to);
        } catch (Exception e) {
            logger.error("Failed to send email with copy to: {}", to, e);
            throw new RuntimeException("Failed to send email", e);
        }
    }
}