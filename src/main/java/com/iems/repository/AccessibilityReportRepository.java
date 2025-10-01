package com.iems.repository;

import java.time.LocalDate;
import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import com.iems.model.entity.AccessibilityReport;
import com.iems.model.enums.DisabilityType;

/**
 * Repository interface for AccessibilityReport entity.
 * Provides comprehensive query methods for accessibility reporting and analytics.
 * 
 * @author IEMS Team
 * @version 1.0.0
 */
@Repository
public interface AccessibilityReportRepository extends JpaRepository<AccessibilityReport, Long>, 
                                                       JpaSpecificationExecutor<AccessibilityReport> {

    // ==================== Basic Queries ====================

    /**
     * Find all accessibility reports for a specific student.
     * 
     * @param studentId the student profile ID
     * @return list of accessibility reports
     */
    List<AccessibilityReport> findByStudentId(Long studentId);

    /**
     * Find all accessibility reports for a specific student with pagination.
     * 
     * @param studentId the student profile ID
     * @param pageable pagination information
     * @return page of accessibility reports
     */
    Page<AccessibilityReport> findByStudentId(Long studentId, Pageable pageable);

    /**
     * Find all accessibility reports for a specific school.
     * 
     * @param schoolId the school ID
     * @return list of accessibility reports
     */
    List<AccessibilityReport> findBySchoolId(Long schoolId);

    /**
     * Find all accessibility reports for a specific school with pagination.
     * 
     * @param schoolId the school ID
     * @param pageable pagination information
     * @return page of accessibility reports
     */
    Page<AccessibilityReport> findBySchoolId(Long schoolId, Pageable pageable);

    /**
     * Find all unresolved accessibility reports.
     * 
     * @return list of unresolved reports
     */
    List<AccessibilityReport> findByResolvedFalse();

    /**
     * Find all unresolved accessibility reports with pagination.
     * 
     * @param pageable pagination information
     * @return page of unresolved reports
     */
    Page<AccessibilityReport> findByResolvedFalse(Pageable pageable);

    /**
     * Find all resolved accessibility reports.
     * 
     * @return list of resolved reports
     */
    List<AccessibilityReport> findByResolvedTrue();

    /**
     * Find reports by related disability type.
     * 
     * @param disabilityType the disability type
     * @return list of reports
     */
    List<AccessibilityReport> findByRelatedDisability(DisabilityType disabilityType);

    /**
     * Find reports by severity level.
     * 
     * @param severity the severity level
     * @return list of reports
     */
    List<AccessibilityReport> findBySeverity(String severity);

    /**
     * Find reports that require follow-up.
     * 
     * @return list of reports requiring follow-up
     */
    List<AccessibilityReport> findByFollowUpRequiredTrue();

    /**
     * Find reports assigned to a specific support staff member.
     * 
     * @param userId the assigned user ID
     * @return list of assigned reports
     */
    List<AccessibilityReport> findByAssignedTo(Long userId);

    // ==================== Date Range Queries ====================

    /**
     * Find accessibility reports for a school within a date range.
     * 
     * @param schoolId the school ID
     * @param startDate the start date (inclusive)
     * @param endDate the end date (inclusive)
     * @return list of reports within the date range
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId " +
           "AND a.reportDate BETWEEN :startDate AND :endDate " +
           "ORDER BY a.reportDate DESC")
    List<AccessibilityReport> findBySchoolIdAndDateRange(
        @Param("schoolId") Long schoolId,
        @Param("startDate") LocalDate startDate,
        @Param("endDate") LocalDate endDate
    );

    /**
     * Find accessibility reports for a student within a date range.
     * 
     * @param studentId the student profile ID
     * @param startDate the start date (inclusive)
     * @param endDate the end date (inclusive)
     * @return list of reports within the date range
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.student.id = :studentId " +
           "AND a.reportDate BETWEEN :startDate AND :endDate " +
           "ORDER BY a.reportDate DESC")
    List<AccessibilityReport> findByStudentIdAndDateRange(
        @Param("studentId") Long studentId,
        @Param("startDate") LocalDate startDate,
        @Param("endDate") LocalDate endDate
    );

    /**
     * Find all reports created after a specific date.
     * 
     * @param date the reference date
     * @return list of reports
     */
    List<AccessibilityReport> findByReportDateAfter(LocalDate date);

    /**
     * Find all reports created before a specific date.
     * 
     * @param date the reference date
     * @return list of reports
     */
    List<AccessibilityReport> findByReportDateBefore(LocalDate date);

    // ==================== Count Queries ====================

    /**
     * Count accessibility reports by school ID.
     * 
     * @param schoolId the school ID
     * @return number of reports
     */
    Long countBySchoolId(Long schoolId);

    /**
     * Count accessibility reports by student ID.
     * 
     * @param studentId the student profile ID
     * @return number of reports
     */
    Long countByStudentId(Long studentId);

    /**
     * Count unresolved reports for a school.
     * 
     * @param schoolId the school ID
     * @return number of unresolved reports
     */
    @Query("SELECT COUNT(a) FROM AccessibilityReport a WHERE a.school.id = :schoolId AND a.resolved = false")
    Long countUnresolvedBySchoolId(@Param("schoolId") Long schoolId);

    /**
     * Count reports by school since a specific date.
     * 
     * @param schoolId the school ID
     * @param startDate the start date
     * @return number of reports
     */
    @Query("SELECT COUNT(a) FROM AccessibilityReport a WHERE a.school.id = :schoolId AND a.reportDate >= :startDate")
    Long countBySchoolIdSince(@Param("schoolId") Long schoolId, @Param("startDate") LocalDate startDate);

    /**
     * Count reports by disability type.
     * 
     * @param disabilityType the disability type
     * @return number of reports
     */
    Long countByRelatedDisability(DisabilityType disabilityType);

    /**
     * Count reports by severity level.
     * 
     * @param severity the severity level
     * @return number of reports
     */
    Long countBySeverity(String severity);

    // ==================== Complex Queries ====================

    /**
     * Find unresolved reports for a school.
     * 
     * @param schoolId the school ID
     * @return list of unresolved reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId AND a.resolved = false " +
           "ORDER BY a.reportDate DESC")
    List<AccessibilityReport> findUnresolvedBySchoolId(@Param("schoolId") Long schoolId);

    /**
     * Find unresolved reports for a school with pagination.
     * 
     * @param schoolId the school ID
     * @param pageable pagination information
     * @return page of unresolved reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId AND a.resolved = false " +
           "ORDER BY a.reportDate DESC")
    Page<AccessibilityReport> findUnresolvedBySchoolId(@Param("schoolId") Long schoolId, Pageable pageable);

    /**
     * Find overdue reports (follow-up required but past follow-up date).
     * 
     * @param currentDate the current date
     * @return list of overdue reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.followUpRequired = true " +
           "AND a.followUpDate < :currentDate AND a.resolved = false " +
           "ORDER BY a.followUpDate ASC")
    List<AccessibilityReport> findOverdueReports(@Param("currentDate") LocalDate currentDate);

    /**
     * Find reports by school and severity level.
     * 
     * @param schoolId the school ID
     * @param severity the severity level
     * @return list of reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId AND a.severity = :severity " +
           "ORDER BY a.reportDate DESC")
    List<AccessibilityReport> findBySchoolIdAndSeverity(
        @Param("schoolId") Long schoolId,
        @Param("severity") String severity
    );

    /**
     * Find reports by school and disability type.
     * 
     * @param schoolId the school ID
     * @param disabilityType the disability type
     * @return list of reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId " +
           "AND a.relatedDisability = :disabilityType " +
           "ORDER BY a.reportDate DESC")
    List<AccessibilityReport> findBySchoolIdAndDisabilityType(
        @Param("schoolId") Long schoolId,
        @Param("disabilityType") DisabilityType disabilityType
    );

    /**
     * Find high-severity unresolved reports for a school.
     * 
     * @param schoolId the school ID
     * @return list of high-severity unresolved reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId " +
           "AND a.resolved = false AND a.severity IN ('HIGH', 'CRITICAL') " +
           "ORDER BY a.reportDate DESC")
    List<AccessibilityReport> findHighSeverityUnresolvedBySchoolId(@Param("schoolId") Long schoolId);

    // ==================== Analytics Queries ====================

    /**
     * Get report statistics by school for a time period.
     * Returns aggregated counts grouped by severity.
     * 
     * @param schoolId the school ID
     * @param startDate the start date
     * @param endDate the end date
     * @return list of objects containing [severity, count]
     */
    @Query("SELECT a.severity, COUNT(a) FROM AccessibilityReport a " +
           "WHERE a.school.id = :schoolId " +
           "AND a.reportDate BETWEEN :startDate AND :endDate " +
           "GROUP BY a.severity")
    List<Object[]> getReportStatsBySchoolAndDateRange(
        @Param("schoolId") Long schoolId,
        @Param("startDate") LocalDate startDate,
        @Param("endDate") LocalDate endDate
    );

    /**
     * Get report statistics by disability type for a school.
     * 
     * @param schoolId the school ID
     * @return list of objects containing [disabilityType, count]
     */
    @Query("SELECT a.relatedDisability, COUNT(a) FROM AccessibilityReport a " +
           "WHERE a.school.id = :schoolId " +
           "GROUP BY a.relatedDisability " +
           "ORDER BY COUNT(a) DESC")
    List<Object[]> getReportStatsByDisabilityType(@Param("schoolId") Long schoolId);

    /**
     * Get monthly report counts for a school.
     * 
     * @param schoolId the school ID
     * @param year the year
     * @return list of objects containing [month, count]
     */
    @Query("SELECT MONTH(a.reportDate), COUNT(a) FROM AccessibilityReport a " +
           "WHERE a.school.id = :schoolId AND YEAR(a.reportDate) = :year " +
           "GROUP BY MONTH(a.reportDate) " +
           "ORDER BY MONTH(a.reportDate)")
    List<Object[]> getMonthlyReportCounts(
        @Param("schoolId") Long schoolId,
        @Param("year") Integer year
    );

    /**
     * Calculate average resolution time in days for a school.
     * 
     * @param schoolId the school ID
     * @return average resolution time in days
     */
    @Query(value = "SELECT AVG(EXTRACT(EPOCH FROM (resolved_date - report_date)) / 86400.0) " +
                   "FROM accessibility_reports " +
                   "WHERE school_id = :schoolId AND resolved = true AND resolved_date IS NOT NULL",
           nativeQuery = true)
    Double getAverageResolutionTimeDays(@Param("schoolId") Long schoolId);

    /**
     * Get resolution rate (percentage) for a school.
     * 
     * @param schoolId the school ID
     * @return resolution rate as percentage (0-100)
     */
    @Query("SELECT (COUNT(CASE WHEN a.resolved = true THEN 1 END) * 100.0 / COUNT(*)) " +
           "FROM AccessibilityReport a WHERE a.school.id = :schoolId")
    Double getResolutionRate(@Param("schoolId") Long schoolId);

    /**
     * Find most common accessibility issues by location for a school.
     * 
     * @param schoolId the school ID
     * @return list of objects containing [location, count]
     */
    @Query("SELECT a.location, COUNT(a) FROM AccessibilityReport a " +
           "WHERE a.school.id = :schoolId AND a.location IS NOT NULL " +
           "GROUP BY a.location " +
           "ORDER BY COUNT(a) DESC")
    List<Object[]> getMostCommonIssuesByLocation(@Param("schoolId") Long schoolId);

    /**
     * Find reports trending over time for analytics dashboard.
     * Groups reports by week for the last 12 weeks.
     * 
     * @param schoolId the school ID
     * @param weeksAgo number of weeks to look back
     * @return list of objects containing [week_number, count]
     */
    @Query(value = "SELECT DATE_TRUNC('week', report_date) as week, COUNT(*) " +
           "FROM accessibility_reports " +
           "WHERE school_id = :schoolId " +
           "AND report_date >= CURRENT_DATE - INTERVAL ':weeksAgo weeks' " +
           "GROUP BY week " +
           "ORDER BY week DESC", nativeQuery = true)
    List<Object[]> getWeeklyReportTrend(
        @Param("schoolId") Long schoolId,
        @Param("weeksAgo") Integer weeksAgo
    );

    // ==================== Search Queries ====================

    /**
     * Search reports by title or description (case-insensitive).
     * 
     * @param searchTerm the search term
     * @return list of matching reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE " +
           "LOWER(a.title) LIKE LOWER(CONCAT('%', :searchTerm, '%')) OR " +
           "LOWER(a.description) LIKE LOWER(CONCAT('%', :searchTerm, '%'))")
    List<AccessibilityReport> searchByTitleOrDescription(@Param("searchTerm") String searchTerm);

    /**
     * Search reports by title or description for a specific school.
     * 
     * @param schoolId the school ID
     * @param searchTerm the search term
     * @return list of matching reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE a.school.id = :schoolId AND " +
           "(LOWER(a.title) LIKE LOWER(CONCAT('%', :searchTerm, '%')) OR " +
           "LOWER(a.description) LIKE LOWER(CONCAT('%', :searchTerm, '%')))")
    List<AccessibilityReport> searchBySchoolAndKeyword(
        @Param("schoolId") Long schoolId,
        @Param("searchTerm") String searchTerm
    );

    /**
     * Advanced search with multiple criteria.
     * 
     * @param schoolId optional school ID filter
     * @param studentId optional student ID filter
     * @param disabilityType optional disability type filter
     * @param severity optional severity filter
     * @param resolved optional resolved status filter
     * @param startDate optional start date filter
     * @param endDate optional end date filter
     * @param pageable pagination information
     * @return page of matching reports
     */
    @Query("SELECT a FROM AccessibilityReport a WHERE " +
           "(:schoolId IS NULL OR a.school.id = :schoolId) AND " +
           "(:studentId IS NULL OR a.student.id = :studentId) AND " +
           "(:disabilityType IS NULL OR a.relatedDisability = :disabilityType) AND " +
           "(:severity IS NULL OR a.severity = :severity) AND " +
           "(:resolved IS NULL OR a.resolved = :resolved) AND " +
           "(:startDate IS NULL OR a.reportDate >= :startDate) AND " +
           "(:endDate IS NULL OR a.reportDate <= :endDate) " +
           "ORDER BY a.reportDate DESC")
    Page<AccessibilityReport> advancedSearch(
        @Param("schoolId") Long schoolId,
        @Param("studentId") Long studentId,
        @Param("disabilityType") DisabilityType disabilityType,
        @Param("severity") String severity,
        @Param("resolved") Boolean resolved,
        @Param("startDate") LocalDate startDate,
        @Param("endDate") LocalDate endDate,
        Pageable pageable
    );

    // ==================== Reporting User Queries ====================

    /**
     * Find all reports created by a specific user.
     * 
     * @param userId the user ID who reported
     * @return list of reports
     */
    List<AccessibilityReport> findByReportedBy(Long userId);

    /**
     * Find recent reports (last N days) for a school.
     * 
     * @param schoolId the school ID
     * @param days number of days to look back
     * @return list of recent reports
     */
       @Query(value = "SELECT * FROM accessibility_reports WHERE school_id = :schoolId " +
                               "AND report_date >= CURRENT_DATE - (:days * INTERVAL '1 day') " +
                               "ORDER BY report_date DESC",
                 nativeQuery = true)
       List<AccessibilityReport> findRecentBySchoolId(
              @Param("schoolId") Long schoolId,
              @Param("days") Integer days
       );
}