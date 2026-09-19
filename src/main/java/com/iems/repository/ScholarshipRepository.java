package com.iems.repository;

import java.time.LocalDate;
import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import com.iems.model.entity.ScholarshipApplication;
import com.iems.model.enums.ScholarshipStatus;

@Repository
public interface ScholarshipRepository extends JpaRepository<ScholarshipApplication, Long> {
    List<ScholarshipApplication> findByStudentId(Long studentId);
    List<ScholarshipApplication> findByStatus(ScholarshipStatus status);
    Page<ScholarshipApplication> findByStatus(ScholarshipStatus status, Pageable pageable);
    
    @Query("SELECT s FROM ScholarshipApplication s WHERE s.status = :status AND s.applicationDate BETWEEN :startDate AND :endDate")
    List<ScholarshipApplication> findByStatusAndDateRange(
        @Param("status") ScholarshipStatus status,
        @Param("startDate") LocalDate startDate,
        @Param("endDate") LocalDate endDate
    );
    
    @Query("SELECT s.createdAt, s.reviewedAt FROM ScholarshipApplication s " +
           "WHERE s.status IN (com.iems.model.enums.ScholarshipStatus.APPROVED, " +
           "com.iems.model.enums.ScholarshipStatus.REJECTED) AND s.reviewedAt IS NOT NULL")
    List<Object[]> findProcessingTimes();

    default Double getAverageProcessingTimeDays() {
        return findProcessingTimes().stream().mapToDouble(row ->
                java.time.Duration.between((java.time.LocalDateTime) row[0],
                        (java.time.LocalDateTime) row[1]).toMillis() / 86400000.0)
                .average().stream().boxed().findFirst().orElse(null);
    }
}
