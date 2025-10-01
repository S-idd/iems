package com.iems.rabbit.model;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Model representing an email sending task.
 */
public class EmailTask implements Serializable {
    private static final long serialVersionUID = 1L;

    private String to;
    private String cc;
    private String bcc;
    private String subject;
    private String body;
    private boolean html;
    private Map<String, String> attachments;
    private LocalDateTime createdAt;
    private Integer priority;

    public EmailTask() {
        this.createdAt = LocalDateTime.now();
        this.html = false;
        this.priority = 5;
        this.attachments = new HashMap<>();
    }

    public EmailTask(String to, String subject, String body) {
        this();
        this.to = to;
        this.subject = subject;
        this.body = body;
    }

    // Getters and Setters
    public String getTo() { return to; }
    public void setTo(String to) { this.to = to; }
    public String getCc() { return cc; }
    public void setCc(String cc) { this.cc = cc; }
    public String getBcc() { return bcc; }
    public void setBcc(String bcc) { this.bcc = bcc; }
    public String getSubject() { return subject; }
    public void setSubject(String subject) { this.subject = subject; }
    public String getBody() { return body; }
    public void setBody(String body) { this.body = body; }
    public boolean isHtml() { return html; }
    public void setHtml(boolean html) { this.html = html; }
    public Map<String, String> getAttachments() { return attachments; }
    public void setAttachments(Map<String, String> attachments) { this.attachments = attachments; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public Integer getPriority() { return priority; }
    public void setPriority(Integer priority) { this.priority = priority; }

    @Override
    public String toString() {
        return "EmailTask{" +
                "to='" + to + '\'' +
                ", subject='" + subject + '\'' +
                ", html=" + html +
                ", priority=" + priority +
                ", createdAt=" + createdAt +
                '}';
    }
}

