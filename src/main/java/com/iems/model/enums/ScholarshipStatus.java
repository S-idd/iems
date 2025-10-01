package com.iems.model.enums;

/**
 * Status of scholarship applications.
 */
public enum ScholarshipStatus {
    /**
     * Application has been submitted and is pending review.
     */
    PENDING,
    
    /**
     * Application is under review by administrators.
     */
    UNDER_REVIEW,
    
    /**
     * Application has been approved.
     */
    APPROVED,
    
    /**
     * Application has been rejected.
     */
    REJECTED,
    
    /**
     * Scholarship funds have been disbursed.
     */
    DISBURSED,
    
    /**
     * Application was cancelled by the applicant.
     */
    CANCELLED
}