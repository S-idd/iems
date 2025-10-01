package com.iems.service;

import com.iems.exception.BadRequestException;
import com.iems.exception.ResourceNotFoundException;
import com.iems.kafka.model.ScholarshipEvent;
import com.iems.model.dto.ScholarshipDto;
import com.iems.model.entity.ScholarshipApplication;
import com.iems.model.entity.StudentProfile;
import com.iems.model.enums.ScholarshipStatus;
import com.iems.rabbit.model.EmailTask;
import com.iems.rabbit.producer.TaskProducer;
import com.iems.repository.ScholarshipRepository;
import com.iems.repository.StudentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service for managing scholarship applications and processing.
 */
@Service
public class ScholarshipService {

    @Autowired
    private ScholarshipRepository scholarshipRepository;

    @Autowired
    private StudentRepository studentRepository;

    @Autowired
    private EventPublisherService eventPublisher;

    @Autowired
    private TaskProducer taskProducer;

    public Page<ScholarshipDto> getAllScholarships(Pageable pageable) {
        return scholarshipRepository.findAll(pageable)
                .map(this::convertToDto);
    }

    @Cacheable(value = "scholarships", key = "#id")
    public ScholarshipDto getScholarshipById(Long id) {
        ScholarshipApplication scholarship = scholarshipRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Scholarship", "id", id));
        return convertToDto(scholarship);
    }

    public List<ScholarshipDto> getScholarshipsByStudent(Long studentId) {
        return scholarshipRepository.findByStudentId(studentId).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public List<ScholarshipDto> getScholarshipsByStatus(ScholarshipStatus status) {
        return scholarshipRepository.findByStatus(status).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public Page<ScholarshipDto> getScholarshipsByStatus(ScholarshipStatus status, Pageable pageable) {
        return scholarshipRepository.findByStatus(status, pageable)
                .map(this::convertToDto);
    }

    @Transactional
    @CacheEvict(value = "scholarships", allEntries = true)
    public ScholarshipDto createScholarship(ScholarshipDto dto) {
        StudentProfile student = studentRepository.findById(dto.getStudentId())
                .orElseThrow(() -> new ResourceNotFoundException("Student", "id", dto.getStudentId()));

        ScholarshipApplication scholarship = new ScholarshipApplication();
        scholarship.setScholarshipName(dto.getScholarshipName());
        scholarship.setStudent(student);
        scholarship.setAmountRequested(dto.getAmountRequested());
        scholarship.setPurpose(dto.getPurpose());
        scholarship.setJustification(dto.getJustification());
        scholarship.setStatus(ScholarshipStatus.PENDING);
        scholarship.setApplicationDate(LocalDate.now());

        ScholarshipApplication saved = scholarshipRepository.save(scholarship);

        // Publish event
        ScholarshipEvent event = new ScholarshipEvent();
        event.setScholarshipId(saved.getId());
        event.setStudentId(student.getId());
        event.setStudentName(student.getUser().getFullName());
        event.setEventType("APPLIED");
        event.setStatus(ScholarshipStatus.PENDING);
        event.setAmount(saved.getAmountRequested());
        eventPublisher.publishScholarshipEvent(event);

        // Send notification email
        sendScholarshipNotification(student, "Scholarship Application Received", 
            String.format("Your scholarship application for '%s' has been received and is under review. " +
                         "Application ID: %d", saved.getScholarshipName(), saved.getId()));

        return convertToDto(saved);
    }

    @Transactional
    @CacheEvict(value = "scholarships", allEntries = true)
    public ScholarshipDto updateScholarship(Long id, ScholarshipDto dto) {
        ScholarshipApplication scholarship = scholarshipRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Scholarship", "id", id));

        // Only allow updates for PENDING scholarships
        if (scholarship.getStatus() != ScholarshipStatus.PENDING) {
            throw new BadRequestException("Can only update pending scholarship applications");
        }

        scholarship.setScholarshipName(dto.getScholarshipName());
        scholarship.setAmountRequested(dto.getAmountRequested());
        scholarship.setPurpose(dto.getPurpose());
        scholarship.setJustification(dto.getJustification());

        ScholarshipApplication updated = scholarshipRepository.save(scholarship);
        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "scholarships", allEntries = true)
    public ScholarshipDto approveScholarship(Long id, BigDecimal approvedAmount, String comments) {
        ScholarshipApplication scholarship = scholarshipRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Scholarship", "id", id));

        if (scholarship.getStatus() != ScholarshipStatus.PENDING && 
            scholarship.getStatus() != ScholarshipStatus.UNDER_REVIEW) {
            throw new BadRequestException("Can only approve pending or under review scholarships");
        }

        if (approvedAmount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new BadRequestException("Approved amount must be greater than zero");
        }

        scholarship.setStatus(ScholarshipStatus.APPROVED);
        scholarship.setAmountApproved(approvedAmount);
        scholarship.setReviewComments(comments);
        scholarship.setReviewedAt(LocalDateTime.now());

        ScholarshipApplication updated = scholarshipRepository.save(scholarship);

        // Publish event
        ScholarshipEvent event = new ScholarshipEvent();
        event.setScholarshipId(updated.getId());
        event.setStudentId(updated.getStudent().getId());
        event.setStudentName(updated.getStudent().getUser().getFullName());
        event.setEventType("APPROVED");
        event.setStatus(ScholarshipStatus.APPROVED);
        event.setAmount(approvedAmount);
        eventPublisher.publishScholarshipEvent(event);

        // Send notification
        sendScholarshipNotification(updated.getStudent(), "Scholarship Approved!", 
            String.format("Congratulations! Your scholarship application for '%s' has been approved. " +
                         "Approved amount: $%.2f. %s", 
                         updated.getScholarshipName(),
                         approvedAmount.doubleValue(),
                         comments != null ? "Comments: " + comments : ""));

        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "scholarships", allEntries = true)
    public ScholarshipDto rejectScholarship(Long id, String comments) {
        ScholarshipApplication scholarship = scholarshipRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Scholarship", "id", id));

        if (scholarship.getStatus() != ScholarshipStatus.PENDING && 
            scholarship.getStatus() != ScholarshipStatus.UNDER_REVIEW) {
            throw new BadRequestException("Can only reject pending or under review scholarships");
        }

        scholarship.setStatus(ScholarshipStatus.REJECTED);
        scholarship.setReviewComments(comments);
        scholarship.setReviewedAt(LocalDateTime.now());

        ScholarshipApplication updated = scholarshipRepository.save(scholarship);

        // Publish event
        ScholarshipEvent event = new ScholarshipEvent();
        event.setScholarshipId(updated.getId());
        event.setStudentId(updated.getStudent().getId());
        event.setStudentName(updated.getStudent().getUser().getFullName());
        event.setEventType("REJECTED");
        event.setStatus(ScholarshipStatus.REJECTED);
        event.setAmount(updated.getAmountRequested());
        eventPublisher.publishScholarshipEvent(event);

        // Send notification
        sendScholarshipNotification(updated.getStudent(), "Scholarship Application Decision", 
            String.format("We regret to inform you that your scholarship application for '%s' " +
                         "was not approved at this time. %s", 
                         updated.getScholarshipName(),
                         comments != null ? "Comments: " + comments : ""));

        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "scholarships", allEntries = true)
    public ScholarshipDto disburseScholarship(Long id, String disbursementReference) {
        ScholarshipApplication scholarship = scholarshipRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Scholarship", "id", id));

        if (scholarship.getStatus() != ScholarshipStatus.APPROVED) {
            throw new BadRequestException("Can only disburse approved scholarships");
        }

        scholarship.setStatus(ScholarshipStatus.DISBURSED);
        scholarship.setDisbursementDate(LocalDate.now());
        scholarship.setDisbursementReference(disbursementReference);

        ScholarshipApplication updated = scholarshipRepository.save(scholarship);

        // Publish event
        ScholarshipEvent event = new ScholarshipEvent();
        event.setScholarshipId(updated.getId());
        event.setStudentId(updated.getStudent().getId());
        event.setStudentName(updated.getStudent().getUser().getFullName());
        event.setEventType("DISBURSED");
        event.setStatus(ScholarshipStatus.DISBURSED);
        event.setAmount(updated.getAmountApproved());
        eventPublisher.publishScholarshipEvent(event);

        // Send notification
        sendScholarshipNotification(updated.getStudent(), "Scholarship Funds Disbursed", 
            String.format("Your scholarship funds of $%.2f have been disbursed. " +
                         "Reference: %s", 
                         updated.getAmountApproved().doubleValue(),
                         disbursementReference));

        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "scholarships", allEntries = true)
    public void cancelScholarship(Long id) {
        ScholarshipApplication scholarship = scholarshipRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Scholarship", "id", id));

        if (scholarship.getStatus() != ScholarshipStatus.PENDING) {
            throw new BadRequestException("Can only cancel pending scholarship applications");
        }

        scholarship.setStatus(ScholarshipStatus.CANCELLED);
        scholarshipRepository.save(scholarship);
    }

    public Map<String, Object> getScholarshipStatistics() {
        Map<String, Object> stats = new HashMap<>();
        
        List<ScholarshipApplication> allScholarships = scholarshipRepository.findAll();
        
        stats.put("totalApplications", (long) allScholarships.size());
        stats.put("pendingApplications", 
            allScholarships.stream().filter(s -> s.getStatus() == ScholarshipStatus.PENDING).count());
        stats.put("approvedApplications", 
            allScholarships.stream().filter(s -> s.getStatus() == ScholarshipStatus.APPROVED).count());
        stats.put("rejectedApplications", 
            allScholarships.stream().filter(s -> s.getStatus() == ScholarshipStatus.REJECTED).count());
        stats.put("disbursedApplications", 
            allScholarships.stream().filter(s -> s.getStatus() == ScholarshipStatus.DISBURSED).count());
        
        // Calculate total amounts
        BigDecimal totalRequested = allScholarships.stream()
                .map(ScholarshipApplication::getAmountRequested)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        stats.put("totalAmountRequested", totalRequested);
        
        BigDecimal totalApproved = allScholarships.stream()
                .filter(s -> s.getAmountApproved() != null)
                .map(ScholarshipApplication::getAmountApproved)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        stats.put("totalAmountApproved", totalApproved);
        
        BigDecimal totalDisbursed = allScholarships.stream()
                .filter(s -> s.getStatus() == ScholarshipStatus.DISBURSED && s.getAmountApproved() != null)
                .map(ScholarshipApplication::getAmountApproved)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        stats.put("totalAmountDisbursed", totalDisbursed);
        
        return stats;
    }

    public Double getAverageProcessingTimeDays() {
        return scholarshipRepository.getAverageProcessingTimeDays();
    }

    private void sendScholarshipNotification(StudentProfile student, String subject, String message) {
        EmailTask emailTask = new EmailTask();
        emailTask.setTo(student.getUser().getEmail());
        emailTask.setSubject(subject);
        emailTask.setBody(message);
        emailTask.setHtml(false);
        taskProducer.sendEmailTask(emailTask);
    }

    private ScholarshipDto convertToDto(ScholarshipApplication scholarship) {
        ScholarshipDto dto = new ScholarshipDto();
        dto.setId(scholarship.getId());
        dto.setScholarshipName(scholarship.getScholarshipName());
        dto.setStudentId(scholarship.getStudent().getId());
        dto.setStudentName(scholarship.getStudent().getUser().getFullName());
        dto.setStudentNumber(scholarship.getStudent().getStudentNumber());
        dto.setAmountRequested(scholarship.getAmountRequested());
        dto.setAmountApproved(scholarship.getAmountApproved());
        dto.setApplicationDate(scholarship.getApplicationDate());
        dto.setStatus(scholarship.getStatus());
        dto.setPurpose(scholarship.getPurpose());
        dto.setJustification(scholarship.getJustification());
        dto.setFinancialNeedScore(scholarship.getFinancialNeedScore());
        dto.setAcademicMeritScore(scholarship.getAcademicMeritScore());
        dto.setReviewComments(scholarship.getReviewComments());
        dto.setDisbursementDate(scholarship.getDisbursementDate());
        return dto;
    }
}