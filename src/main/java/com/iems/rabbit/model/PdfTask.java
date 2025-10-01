package com.iems.rabbit.model;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Model representing a PDF generation task.
 */
public class PdfTask implements Serializable {
    private static final long serialVersionUID = 1L;

    private String templateName;
    private String documentType;
    private Long entityId;
    private String outputPath;
    private Map<String, Object> data;
    private LocalDateTime createdAt;
    private String requestedBy;

    public PdfTask() {
        this.createdAt = LocalDateTime.now();
        this.data = new HashMap<>();
    }

    public PdfTask(String templateName, String documentType, Long entityId) {
        this();
        this.templateName = templateName;
        this.documentType = documentType;
        this.entityId = entityId;
    }

    // Getters and Setters
    public String getTemplateName() { return templateName; }
    public void setTemplateName(String templateName) { this.templateName = templateName; }
    public String getDocumentType() { return documentType; }
    public void setDocumentType(String documentType) { this.documentType = documentType; }
    public Long getEntityId() { return entityId; }
    public void setEntityId(Long entityId) { this.entityId = entityId; }
    public String getOutputPath() { return outputPath; }
    public void setOutputPath(String outputPath) { this.outputPath = outputPath; }
    public Map<String, Object> getData() { return data; }
    public void setData(Map<String, Object> data) { this.data = data; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public String getRequestedBy() { return requestedBy; }
    public void setRequestedBy(String requestedBy) { this.requestedBy = requestedBy; }

    @Override
    public String toString() {
        return "PdfTask{" +
                "templateName='" + templateName + '\'' +
                ", documentType='" + documentType + '\'' +
                ", entityId=" + entityId +
                ", outputPath='" + outputPath + '\'' +
                ", createdAt=" + createdAt +
                '}';
    }
}

