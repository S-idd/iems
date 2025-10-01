package com.iems.model.enums;

/**
 * User roles for role-based access control in the IEMS system.
 */
public enum UserRole {
    /**
     * System administrator with full access.
     */
    ADMIN,
    
    /**
     * School/college administrator managing institution.
     */
    SCHOOL_ADMIN,
    
    /**
     * Teacher with access to courses and classrooms.
     */
    TEACHER,
    
    /**
     * Student enrolled in the institution.
     */
    STUDENT,
    
    /**
     * Parent/guardian with limited access to student information.
     */
    PARENT,
    
    /**
     * Support staff for accessibility and accommodations.
     */
    SUPPORT
}