package com.iems.service;

import com.iems.exception.ResourceNotFoundException;
import com.iems.kafka.model.AccessibilityEvent;
import com.iems.model.dto.AccessibilityReportDto;
import com.iems.model.entity.AccessibilityReport;
import com.iems.model.entity.School;
import com.iems.model.entity.StudentProfile;
import com.iems.model.enums.DisabilityType;
import com.iems.repository.AccessibilityReportRepository;
import com.iems.repository.SchoolRepository;
import com.iems.repository.StudentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service for managing accessibility reports and accommodations.
 */
@Service
public class AccessibilityService {

    @Autowired
    private AccessibilityReportRepository accessibilityReportRepository;

    @Autowired
    private StudentRepository studentRepository;

    @Autowired
    private SchoolRepository schoolRepository;

    @Autowired
    private EventPublisherService eventPublisher;

    public Page<AccessibilityReportDto> getAllReports(Pageable pageable) {
        return accessibilityReportRepository.findAll(pageable)
                .map(this::convertToDto);
    }

    @Cacheable(value = "accessibility-reports", key = "#id")
    public AccessibilityReportDto getReportById(Long id) {
        AccessibilityReport report = accessibilityReportRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AccessibilityReport", "id", id));
        return convertToDto(report);
    }

    public List<AccessibilityReportDto> getReportsBySchool(Long schoolId) {
        return accessibilityReportRepository.findBySchoolId(schoolId).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public List<AccessibilityReportDto> getReportsByStudent(Long studentId) {
        return accessibilityReportRepository.findByStudentId(studentId).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public Page<AccessibilityReportDto> getUnresolvedReports(Pageable pageable) {
        return accessibilityReportRepository.findByResolvedFalse(pageable)
                .map(this::convertToDto);
    }

    public List<AccessibilityReportDto> getUnresolvedReportsBySchool(Long schoolId) {
        return accessibilityReportRepository.findUnresolvedBySchoolId(schoolId).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public List<AccessibilityReportDto> getOverdueReports() {
        return accessibilityReportRepository.findOverdueReports(LocalDate.now()).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public Page<AccessibilityReportDto> searchReports(Long schoolId, Long studentId,
                                                      DisabilityType disabilityType, String severity,
                                                      Boolean resolved, LocalDate startDate,
                                                      LocalDate endDate, Pageable pageable) {
        return accessibilityReportRepository.advancedSearch(
                schoolId, studentId, disabilityType, severity, resolved, startDate, endDate, pageable
        ).map(this::convertToDto);
    }

    @Transactional
    @CacheEvict(value = "accessibility-reports", allEntries = true)
    public AccessibilityReportDto createReport(AccessibilityReportDto dto) {
        StudentProfile student = studentRepository.findById(dto.getStudentId())
                .orElseThrow(() -> new ResourceNotFoundException("Student", "id", dto.getStudentId()));

        School school = schoolRepository.findById(dto.getSchoolId())
                .orElseThrow(() -> new ResourceNotFoundException("School", "id", dto.getSchoolId()));

        AccessibilityReport report = new AccessibilityReport();
        report.setStudent(student);
        report.setSchool(school);
        report.setTitle(dto.getTitle());
        report.setDescription(dto.getDescription());
        report.setRelatedDisability(dto.getRelatedDisability());
        report.setIncidentDate(dto.getIncidentDate());
        report.setLocation(dto.getLocation());
        report.setSeverity(dto.getSeverity());
        report.setReportDate(LocalDate.now());
        report.setResolved(false);

        AccessibilityReport saved = accessibilityReportRepository.save(report);

        // Publish event to Kafka
        AccessibilityEvent event = new AccessibilityEvent();
        event.setId(saved.getId());
        event.setSchoolId(school.getId());
        event.setSchoolName(school.getName());
        event.setStudentId(student.getId());
        event.setStudentName(student.getUser().getFullName());
        event.setEventType("REPORT_CREATED");
        event.setDisabilityType(saved.getRelatedDisability());
        event.setSeverity(saved.getSeverity());
        eventPublisher.publishAccessibilityEvent(event);

        return convertToDto(saved);
    }

    @Transactional
    @CacheEvict(value = "accessibility-reports", allEntries = true)
    public AccessibilityReportDto updateReport(Long id, AccessibilityReportDto dto) {
        AccessibilityReport report = accessibilityReportRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AccessibilityReport", "id", id));

        report.setTitle(dto.getTitle());
        report.setDescription(dto.getDescription());
        report.setRelatedDisability(dto.getRelatedDisability());
        report.setIncidentDate(dto.getIncidentDate());
        report.setLocation(dto.getLocation());
        report.setSeverity(dto.getSeverity());
        report.setActionTaken(dto.getActionTaken());
        report.setFollowUpRequired(dto.getFollowUpRequired());
        report.setFollowUpDate(dto.getFollowUpDate());

        AccessibilityReport updated = accessibilityReportRepository.save(report);

        // Publish update event
        AccessibilityEvent event = new AccessibilityEvent();
        event.setId(updated.getId());
        event.setSchoolId(updated.getSchool().getId());
        event.setSchoolName(updated.getSchool().getName());
        event.setStudentId(updated.getStudent().getId());
        event.setStudentName(updated.getStudent().getUser().getFullName());
        event.setEventType("REPORT_UPDATED");
        event.setDisabilityType(updated.getRelatedDisability());
        event.setSeverity(updated.getSeverity());
        eventPublisher.publishAccessibilityEvent(event);

        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "accessibility-reports", allEntries = true)
    public AccessibilityReportDto resolveReport(Long id) {
        AccessibilityReport report = accessibilityReportRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AccessibilityReport", "id", id));

        report.setResolved(true);
        report.setResolvedDate(LocalDate.now());

        AccessibilityReport resolved = accessibilityReportRepository.save(report);

        // Publish resolution event
        AccessibilityEvent event = new AccessibilityEvent();
        event.setId(resolved.getId());
        event.setSchoolId(resolved.getSchool().getId());
        event.setSchoolName(resolved.getSchool().getName());
        event.setStudentId(resolved.getStudent().getId());
        event.setStudentName(resolved.getStudent().getUser().getFullName());
        event.setEventType("REPORT_RESOLVED");
        event.setDisabilityType(resolved.getRelatedDisability());
        event.setSeverity(resolved.getSeverity());
        eventPublisher.publishAccessibilityEvent(event);

        return convertToDto(resolved);
    }

    @Transactional
    @CacheEvict(value = "accessibility-reports", allEntries = true)
    public AccessibilityReportDto assignReport(Long id, Long assignedTo) {
        AccessibilityReport report = accessibilityReportRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AccessibilityReport", "id", id));

        report.setAssignedTo(assignedTo);
        AccessibilityReport updated = accessibilityReportRepository.save(report);

        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "accessibility-reports", allEntries = true)
    public void deleteReport(Long id) {
        AccessibilityReport report = accessibilityReportRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AccessibilityReport", "id", id));
        accessibilityReportRepository.delete(report);
    }

    public Map<String, Object> getSchoolStatistics(Long schoolId) {
        Map<String, Object> stats = new HashMap<>();
        
        stats.put("totalReports", accessibilityReportRepository.countBySchoolId(schoolId));
        stats.put("unresolvedReports", accessibilityReportRepository.countUnresolvedBySchoolId(schoolId));
        stats.put("resolvedReports", 
            accessibilityReportRepository.countBySchoolId(schoolId) - 
            accessibilityReportRepository.countUnresolvedBySchoolId(schoolId));
        stats.put("resolutionRate", accessibilityReportRepository.getResolutionRate(schoolId));
        stats.put("averageResolutionDays", accessibilityReportRepository.getAverageResolutionTimeDays(schoolId));
        stats.put("studentsWithDisabilities", studentRepository.countStudentsWithDisabilitiesBySchool(schoolId));
        
        return stats;
    }

    public Map<DisabilityType, Long> getDisabilityBreakdown(Long schoolId) {
        List<Object[]> results = accessibilityReportRepository.getReportStatsByDisabilityType(schoolId);
        Map<DisabilityType, Long> breakdown = new HashMap<>();
        
        for (Object[] result : results) {
            DisabilityType type = (DisabilityType) result[0];
            Long count = (Long) result[1];
            if (type != null) {
                breakdown.put(type, count);
            }
        }
        
        return breakdown;
    }

    public List<Map<String, Object>> getWeeklyTrend(Long schoolId, Integer weeks) {
        List<Object[]> results = accessibilityReportRepository.getWeeklyReportTrend(schoolId, weeks);
        return results.stream().map(result -> {
            Map<String, Object> weekData = new HashMap<>();
            weekData.put("week", result[0]);
            weekData.put("count", result[1]);
            return weekData;
        }).collect(Collectors.toList());
    }

    public Double getResolutionRate(Long schoolId) {
        return accessibilityReportRepository.getResolutionRate(schoolId);
    }

    public Double getAverageResolutionTime(Long schoolId) {
        return accessibilityReportRepository.getAverageResolutionTimeDays(schoolId);
    }

    private AccessibilityReportDto convertToDto(AccessibilityReport report) {
        AccessibilityReportDto dto = new AccessibilityReportDto();
        dto.setId(report.getId());
        dto.setStudentId(report.getStudent().getId());
        dto.setStudentName(report.getStudent().getUser().getFullName());
        dto.setSchoolId(report.getSchool().getId());
        dto.setSchoolName(report.getSchool().getName());
        dto.setTitle(report.getTitle());
        dto.setDescription(report.getDescription());
        dto.setRelatedDisability(report.getRelatedDisability());
        dto.setReportDate(report.getReportDate());
        dto.setIncidentDate(report.getIncidentDate());
        dto.setLocation(report.getLocation());
        dto.setSeverity(report.getSeverity());
        dto.setActionTaken(report.getActionTaken());
        dto.setFollowUpRequired(report.getFollowUpRequired());
        dto.setFollowUpDate(report.getFollowUpDate());
        dto.setResolved(report.getResolved());
        dto.setResolvedDate(report.getResolvedDate());
        return dto;
    }
}