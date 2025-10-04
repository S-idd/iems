package com.iems.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.iems.model.dto.AccessibilityReportDto;
import com.iems.service.AccessibilityService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;

/**
 * REST controller for accessibility reports management.
 */
@RestController
@RequestMapping("/api/accessibility")
@Tag(name = "Accessibility Reports", description = "Accessibility reports management endpoints")
@SecurityRequirement(name = "bearerAuth")
public class AccessibilityController {

    @Autowired
    private AccessibilityService accessibilityService;

    @PostMapping
    @Operation(summary = "Create accessibility report", description = "Create a new accessibility report")
    public ResponseEntity<AccessibilityReportDto> createReport(
            @RequestBody AccessibilityReportDto reportDto) {
        AccessibilityReportDto created = accessibilityService.createReport(reportDto);
        return ResponseEntity.ok(created);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get report by ID", description = "Retrieve an accessibility report by its ID")
    public ResponseEntity<AccessibilityReportDto> getReportById(@PathVariable Long id) {
        AccessibilityReportDto report = accessibilityService.getReportById(id);
        return ResponseEntity.ok(report);
    }

    @GetMapping
    @Operation(summary = "Get all reports", description = "Retrieve paginated accessibility reports")
    public ResponseEntity<Page<AccessibilityReportDto>> getAllReports(Pageable pageable) {
        Page<AccessibilityReportDto> reports = accessibilityService.getAllReports(pageable);
        return ResponseEntity.ok(reports);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update report", description = "Update an existing accessibility report by ID")
    public ResponseEntity<AccessibilityReportDto> updateReport(
            @PathVariable Long id,
            @RequestBody AccessibilityReportDto reportDto) {
        AccessibilityReportDto updated = accessibilityService.updateReport(id, reportDto);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete report", description = "Delete an accessibility report by ID")
    public ResponseEntity<Void> deleteReport(@PathVariable Long id) {
        accessibilityService.deleteReport(id);
        return ResponseEntity.noContent().build();
    }
}
