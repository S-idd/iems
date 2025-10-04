package com.iems.controller;

import java.util.List;

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
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.iems.model.dto.ApiResponse;
import com.iems.model.dto.SchoolDto;
import com.iems.model.dto.SchoolResponseDTO;
import com.iems.service.SchoolService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/schools")
public class SchoolController {

    @Autowired
    private SchoolService schoolService;

    // Get all active schools
    @GetMapping("/active")
    public ResponseEntity<ApiResponse<List<SchoolDto>>> getAllActiveSchools() {
        List<SchoolDto> schools = schoolService.getAllActiveSchools();
        return ResponseEntity.ok(ApiResponse.success("Active schools retrieved", schools));
    }

    // Get schools with pagination
    @GetMapping
    public ResponseEntity<ApiResponse<Page<SchoolDto>>> getSchools(Pageable pageable) {
        Page<SchoolDto> schools = schoolService.getSchools(pageable);
        return ResponseEntity.ok(ApiResponse.success("Schools retrieved", schools));
    }

    // Get school by ID
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<SchoolDto>> getSchoolById(@PathVariable Long id) {
        SchoolDto school = schoolService.getSchoolById(id);
        return ResponseEntity.ok(ApiResponse.success("School retrieved", school));
    }

    // Create a new school
    @PostMapping
    public ResponseEntity<ApiResponse<SchoolDto>> createSchool(@Valid @RequestBody SchoolDto schoolDto) {
        SchoolDto createdSchool = schoolService.createSchool(schoolDto);
        return ResponseEntity.ok(ApiResponse.success("School created successfully", createdSchool));
    }

    // Update a school
    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<SchoolDto>> updateSchool(@PathVariable Long id, @Valid @RequestBody SchoolDto schoolDto) {
        SchoolDto updatedSchool = schoolService.updateSchool(id, schoolDto);
        return ResponseEntity.ok(ApiResponse.success("School updated successfully", updatedSchool));
    }

    // Soft delete a school
    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteSchool(@PathVariable Long id) {
        schoolService.deleteSchool(id);
        return ResponseEntity.ok(ApiResponse.success("School deleted successfully", null));
    }

    // Get schools by city
    @GetMapping("/city/{city}")
    public ResponseEntity<ApiResponse<List<SchoolResponseDTO>>> getSchoolsByCity(@PathVariable String city) {
        List<SchoolResponseDTO> schools = schoolService.getSchoolsByCity(city);
        return ResponseEntity.ok(ApiResponse.success("Schools by city retrieved", schools));
    }

    // Get schools by state
    @GetMapping("/state/{state}")
    public ResponseEntity<ApiResponse<List<SchoolResponseDTO>>> getSchoolsByState(@PathVariable String state) {
        List<SchoolResponseDTO> schools = schoolService.getSchoolsByState(state);
        return ResponseEntity.ok(ApiResponse.success("Schools by state retrieved", schools));
    }

    // Get schools by district
    @GetMapping("/district/{district}")
    public ResponseEntity<ApiResponse<List<SchoolResponseDTO>>> getSchoolsByDistrict(@PathVariable String district) {
        List<SchoolResponseDTO> schools = schoolService.getSchoolsByDistrict(district);
        return ResponseEntity.ok(ApiResponse.success("Schools by district retrieved", schools));
    }

    // Search schools
    @GetMapping("/search")
    public ResponseEntity<ApiResponse<List<SchoolResponseDTO>>> searchSchools(@RequestParam String keyword) {
        List<SchoolResponseDTO> schools = schoolService.searchSchools(keyword);
        return ResponseEntity.ok(ApiResponse.success("Search results retrieved", schools));
    }

    // Get school by code
    @GetMapping("/code/{code}")
    public ResponseEntity<ApiResponse<SchoolResponseDTO>> getSchoolByCode(@PathVariable String code) {
        SchoolResponseDTO school = schoolService.getSchoolByCode(code);
        return ResponseEntity.ok(ApiResponse.success("School retrieved by code", school));
    }
}
