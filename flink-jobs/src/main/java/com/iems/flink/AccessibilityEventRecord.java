package com.iems.flink;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.io.Serializable;
import java.util.Objects;

/**
 * Represents an accessibility event record from the Kafka topic.
 * Fields match the app's AccessibilityEvent model.
 */
public class AccessibilityEventRecord implements Serializable {

    private static final long serialVersionUID = 1L;

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

    /**
     * Event timestamp in epoch millis (UTC). Accepts null if unknown.
     */
    @JsonProperty("timestamp")
    private Long timestamp;

    public AccessibilityEventRecord() {
    }

    public AccessibilityEventRecord(String eventId, Long schoolId, String schoolName,
                                    Long studentId, String studentName, String eventType,
                                    String disabilityType, Integer severity, Long timestamp) {
        this.eventId = eventId;
        this.schoolId = schoolId;
        this.schoolName = schoolName;
        this.studentId = studentId;
        this.studentName = studentName;
        this.eventType = eventType;
        this.disabilityType = disabilityType;
        this.severity = severity;
        this.timestamp = timestamp;
    }

    public String getEventId() {
        return eventId;
    }
    public void setEventId(String eventId) {
        this.eventId = eventId;
    }

    public Long getSchoolId() {
        return schoolId;
    }
    public void setSchoolId(Long schoolId) {
        this.schoolId = schoolId;
    }

    public String getSchoolName() {
        return schoolName;
    }
    public void setSchoolName(String schoolName) {
        this.schoolName = schoolName;
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

    public String getDisabilityType() {
        return disabilityType;
    }
    public void setDisabilityType(String disabilityType) {
        this.disabilityType = disabilityType;
    }

    public Integer getSeverity() {
        return severity;
    }
    public void setSeverity(Integer severity) {
        this.severity = severity;
    }

    public Long getTimestamp() {
        return timestamp;
    }
    public void setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
    }

    @Override
    public String toString() {
        return "AccessibilityEventRecord{" +
                "eventId='" + eventId + '\'' +
                ", schoolId=" + schoolId +
                ", schoolName='" + schoolName + '\'' +
                ", studentId=" + studentId +
                ", studentName='" + studentName + '\'' +
                ", eventType='" + eventType + '\'' +
                ", disabilityType='" + disabilityType + '\'' +
                ", severity=" + severity +
                ", timestamp=" + timestamp +
                '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof AccessibilityEventRecord)) return false;
        AccessibilityEventRecord that = (AccessibilityEventRecord) o;
        return Objects.equals(eventId, that.eventId) &&
               Objects.equals(schoolId, that.schoolId) &&
               Objects.equals(studentId, that.studentId) &&
               Objects.equals(timestamp, that.timestamp);
    }

    @Override
    public int hashCode() {
        return Objects.hash(eventId, schoolId, studentId, timestamp);
    }
}