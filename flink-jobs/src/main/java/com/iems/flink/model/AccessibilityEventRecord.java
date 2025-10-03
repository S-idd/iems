package com.iems.flink.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Represents an accessibility event record from the Kafka topic.
 * Fields match the app's AccessibilityEvent model.
 */
public class AccessibilityEventRecord {

    @JsonProperty("eventId")
    private String eventId;

    @JsonProperty("schoolId")
    private Long schoolId;

    @JsonProperty("schoolName")
    private String schoolName;

    @JsonProperty("studentId")
    private Long studentId;

    @JsonProperty("studentName")
    private String studentName;

    @JsonProperty("eventType")
    private String eventType;

    @JsonProperty("disabilityType")
    private String disabilityType;

    @JsonProperty("severity")
    private Integer severity;

    @JsonProperty("timestamp")
    private Long timestamp;

    // Getters and Setters
    public String getEventId() { return eventId; }
    public void setEventId(String eventId) { this.eventId = eventId; }

    public Long getSchoolId() { return schoolId; }
    public void setSchoolId(Long schoolId) { this.schoolId = schoolId; }

    public String getSchoolName() { return schoolName; }
    public void setSchoolName(String schoolName) { this.schoolName = schoolName; }

    public Long getStudentId() { return studentId; }
    public void setStudentId(Long studentId) { this.studentId = studentId; }

    public String getStudentName() { return studentName; }
    public void setStudentName(String studentName) { this.studentName = studentName; }

    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }

    public String getDisabilityType() { return disabilityType; }
    public void setDisabilityType(String disabilityType) { this.disabilityType = disabilityType; }

    public Integer getSeverity() { return severity; }
    public void setSeverity(Integer severity) { this.severity = severity; }

    public Long getTimestamp() { return timestamp; }
    public void setTimestamp(Long timestamp) { this.timestamp = timestamp; }

    @Override
    public String toString() {
        return "AccessibilityEventRecord{" +
                "eventId='" + eventId + '\'' +
                ", schoolId=" + schoolId +
                ", timestamp=" + timestamp +
                '}';
    }
}