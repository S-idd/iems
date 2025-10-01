package com.iems.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import com.iems.model.entity.StudentProfile;

@Repository
public interface StudentRepository extends JpaRepository<StudentProfile, Long> {
    Optional<StudentProfile> findByStudentNumber(String studentNumber);
    Optional<StudentProfile> findByUserId(Long userId);
    List<StudentProfile> findByHasDisabilityTrue();
    
    @Query("SELECT s FROM StudentProfile s WHERE s.user.school.id = :schoolId")
    List<StudentProfile> findBySchoolId(@Param("schoolId") Long schoolId);
    
    @Query("SELECT COUNT(s) FROM StudentProfile s WHERE s.hasDisability = true AND s.user.school.id = :schoolId")
    Long countStudentsWithDisabilitiesBySchool(@Param("schoolId") Long schoolId);
}