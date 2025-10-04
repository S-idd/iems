package com.iems.controller;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.iems.model.dto.ScholarshipDto;
import com.iems.model.enums.ScholarshipStatus;
import com.iems.security.UserPrincipal;
import com.iems.service.ScholarshipService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;

/**
 * REST controller for managing scholarship applications.
 */
@RestController
@RequestMapping("/api/scholarships")
@Tag(name = "Scholarships", description = "Scholarship application management endpoints")
@SecurityRequirement(name = "bearerAuth")
public class ScholarshipController {

    @Autowired
    private ScholarshipService scholarshipService;

    // ----------------- Student Actions -----------------

    @PostMapping
    @PreAuthorize("hasRole('STUDENT')")
    @Operation(summary = "Apply for scholarship", description = "Students can submit a new scholarship application")
    public ResponseEntity<ScholarshipDto> createScholarship(
            @AuthenticationPrincipal UserPrincipal user,
            @Valid @RequestBody ScholarshipDto scholarshipDto) {
        // Student ID will be taken from DTO or userPrincipal if needed
        scholarshipDto.setStudentId(user.getId());
        return ResponseEntity.ok(scholarshipService.createScholarship(scholarshipDto));
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('STUDENT')")
    @Operation(summary = "Update scholarship", description = "Students can update a pending scholarship application")
    public ResponseEntity<ScholarshipDto> updateScholarship(
            @PathVariable Long id,
            @Valid @RequestBody ScholarshipDto dto) {
        return ResponseEntity.ok(scholarshipService.updateScholarship(id, dto));
    }

    @DeleteMapping("/{id}/cancel")
    @PreAuthorize("hasRole('STUDENT')")
    @Operation(summary = "Cancel scholarship", description = "Cancel a pending scholarship application")
    public ResponseEntity<Void> cancelScholarship(@PathVariable Long id) {
        scholarshipService.cancelScholarship(id);
        return ResponseEntity.noContent().build();
    }

    // ----------------- Admin Actions -----------------

    @PutMapping("/{id}/approve")
    @PreAuthorize("hasRole('ADMIN')")
    @Operation(summary = "Approve scholarship", description = "Approve a scholarship with an approved amount and comments")
    public ResponseEntity<ScholarshipDto> approveScholarship(
            @PathVariable Long id,
            @RequestParam BigDecimal approvedAmount,
            @RequestParam(required = false) String comments) {
        return ResponseEntity.ok(scholarshipService.approveScholarship(id, approvedAmount, comments));
    }

    @PutMapping("/{id}/reject")
    @PreAuthorize("hasRole('ADMIN')")
    @Operation(summary = "Reject scholarship", description = "Reject a scholarship with comments")
    public ResponseEntity<ScholarshipDto> rejectScholarship(
            @PathVariable Long id,
            @RequestParam(required = false) String comments) {
        return ResponseEntity.ok(scholarshipService.rejectScholarship(id, comments));
    }

    @PutMapping("/{id}/disburse")
    @PreAuthorize("hasRole('ADMIN')")
    @Operation(summary = "Disburse scholarship", description = "Mark a scholarship as disbursed with reference number")
    public ResponseEntity<ScholarshipDto> disburseScholarship(
            @PathVariable Long id,
            @RequestParam String reference) {
        return ResponseEntity.ok(scholarshipService.disburseScholarship(id, reference));
    }

    // ----------------- Public / Shared Actions -----------------

    @GetMapping
    @PreAuthorize("hasAnyRole('ADMIN','STUDENT')")
    @Operation(summary = "List scholarships", description = "Get all scholarships with pagination")
    public ResponseEntity<Page<ScholarshipDto>> getAllScholarships(Pageable pageable) {
        return ResponseEntity.ok(scholarshipService.getAllScholarships(pageable));
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('ADMIN','STUDENT')")
    @Operation(summary = "Get scholarship details", description = "Fetch scholarship by ID")
    public ResponseEntity<ScholarshipDto> getScholarshipById(@PathVariable Long id) {
        return ResponseEntity.ok(scholarshipService.getScholarshipById(id));
    }

    @GetMapping("/student/{studentId}")
    @PreAuthorize("hasAnyRole('ADMIN','STUDENT')")
    @Operation(summary = "Get scholarships by student", description = "Fetch scholarships for a specific student")
    public ResponseEntity<List<ScholarshipDto>> getScholarshipsByStudent(@PathVariable Long studentId) {
        return ResponseEntity.ok(scholarshipService.getScholarshipsByStudent(studentId));
    }

    @GetMapping("/status/{status}")
    @PreAuthorize("hasAnyRole('ADMIN','STUDENT')")
    @Operation(summary = "Get scholarships by status", description = "Fetch scholarships by application status")
    public ResponseEntity<List<ScholarshipDto>> getScholarshipsByStatus(@PathVariable ScholarshipStatus status) {
        return ResponseEntity.ok(scholarshipService.getScholarshipsByStatus(status));
    }

    @GetMapping("/status/{status}/paged")
    @PreAuthorize("hasAnyRole('ADMIN','STUDENT')")
    @Operation(summary = "Get paginated scholarships by status", description = "Fetch scholarships by status with pagination")
    public ResponseEntity<Page<ScholarshipDto>> getScholarshipsByStatusPaged(
            @PathVariable ScholarshipStatus status,
            Pageable pageable) {
        return ResponseEntity.ok(scholarshipService.getScholarshipsByStatus(status, pageable));
    }

    // ----------------- Statistics -----------------

    @GetMapping("/stats")
    @PreAuthorize("hasRole('ADMIN')")
    @Operation(summary = "Scholarship statistics", description = "Get aggregated statistics of all scholarship applications")
    public ResponseEntity<Map<String, Object>> getScholarshipStatistics() {
        return ResponseEntity.ok(scholarshipService.getScholarshipStatistics());
    }

    @GetMapping("/avg-processing-time")
    @PreAuthorize("hasRole('ADMIN')")
    @Operation(summary = "Average processing time", description = "Get average processing time in days")
    public ResponseEntity<Double> getAverageProcessingTime() {
        return ResponseEntity.ok(scholarshipService.getAverageProcessingTimeDays());
    }
}
