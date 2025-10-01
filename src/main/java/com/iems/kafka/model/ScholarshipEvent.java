package com.iems.kafka.model;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.iems.model.enums.ScholarshipStatus;

public class ScholarshipEvent {
    private Long scholarshipId;
    private Long studentId;
    private String studentName;
    private String eventType;
    private ScholarshipStatus status;
    private BigDecimal amount;
    private LocalDateTime timestamp;

    public ScholarshipEvent() {
        this.timestamp = LocalDateTime.now();
    }

    // Getters and Setters
    public Long getScholarshipId() {
        return scholarshipId;
    }

    public void setScholarshipId(Long scholarshipId) {
        this.scholarshipId = scholarshipId;
    }

    public Long getStudentId() {
        return studentId;
    }

    public void setStudentId(Long studentId) {
        this.studentId = studentId;
    }

    public String getStudentName() {
        return studentName;
    }

    public void setStudentName(String studentName) {
        this.studentName = studentName;
    }

    public String getEventType() {
        return eventType;
    }

    public void setEventType(String eventType) {
        this.eventType = eventType;
    }

    public ScholarshipStatus getStatus() {
        return status;
    }

    public void setStatus(ScholarshipStatus status) {
        this.status = status;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    @Override
    public String toString() {
        return "ScholarshipEvent{" +
                "scholarshipId=" + scholarshipId +
                ", studentId=" + studentId +
                ", eventType='" + eventType + '\'' +
                ", status=" + status +
                ", amount=" + amount +
                ", timestamp=" + timestamp +
                '}';
    }
}