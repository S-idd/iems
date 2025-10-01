package com.iems.model.dto;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.iems.model.enums.ScholarshipStatus;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public class ScholarshipDto {
    private Long id;

    @NotBlank
    private String scholarshipName;

    @NotNull
    private Long studentId;

    private String studentName;
    private String studentNumber;

    @NotNull
    @Positive
    private BigDecimal amountRequested;

    private BigDecimal amountApproved;
    private LocalDate applicationDate;
    private ScholarshipStatus status;
    private String purpose;
    private String justification;
    private Integer financialNeedScore;
    private Integer academicMeritScore;
    private String reviewComments;
    private LocalDate disbursementDate;

    // Getters and Setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getScholarshipName() {
        return scholarshipName;
    }

    public void setScholarshipName(String scholarshipName) {
        this.scholarshipName = scholarshipName;
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

    public String getStudentNumber() {
        return studentNumber;
    }

    public void setStudentNumber(String studentNumber) {
        this.studentNumber = studentNumber;
    }

    public BigDecimal getAmountRequested() {
        return amountRequested;
    }

    public void setAmountRequested(BigDecimal amountRequested) {
        this.amountRequested = amountRequested;
    }

    public BigDecimal getAmountApproved() {
        return amountApproved;
    }

    public void setAmountApproved(BigDecimal amountApproved) {
        this.amountApproved = amountApproved;
    }

    public LocalDate getApplicationDate() {
        return applicationDate;
    }

    public void setApplicationDate(LocalDate applicationDate) {
        this.applicationDate = applicationDate;
    }

    public ScholarshipStatus getStatus() {
        return status;
    }

    public void setStatus(ScholarshipStatus status) {
        this.status = status;
    }

    public String getPurpose() {
        return purpose;
    }

    public void setPurpose(String purpose) {
        this.purpose = purpose;
    }

    public String getJustification() {
        return justification;
    }

    public void setJustification(String justification) {
        this.justification = justification;
    }

    public Integer getFinancialNeedScore() {
        return financialNeedScore;
    }

    public void setFinancialNeedScore(Integer financialNeedScore) {
        this.financialNeedScore = financialNeedScore;
    }

    public Integer getAcademicMeritScore() {
        return academicMeritScore;
    }

    public void setAcademicMeritScore(Integer academicMeritScore) {
        this.academicMeritScore = academicMeritScore;
    }

    public String getReviewComments() {
        return reviewComments;
    }

    public void setReviewComments(String reviewComments) {
        this.reviewComments = reviewComments;
    }

    public LocalDate getDisbursementDate() {
        return disbursementDate;
    }

    public void setDisbursementDate(LocalDate disbursementDate) {
        this.disbursementDate = disbursementDate;
    }
}