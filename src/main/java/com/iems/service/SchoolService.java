package com.iems.service;

import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.iems.exception.ResourceNotFoundException;
import com.iems.exception.BadRequestException;
import com.iems.model.dto.SchoolDto;
import com.iems.model.dto.SchoolResponseDTO;
import com.iems.model.entity.School;
import com.iems.repository.SchoolRepository;

/**
 * Service for managing schools.
 */
@Service
public class SchoolService {

    @Autowired
    private SchoolRepository schoolRepository;

    /**
     * Get all active schools with caching.
     */
    @Cacheable(value = "schools", key = "'all_active'")
    public List<SchoolDto> getAllActiveSchools() {
        return schoolRepository.findByActiveTrue().stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    /**
     * Get schools with pagination.
     */
    public Page<SchoolDto> getSchools(Pageable pageable) {
        return schoolRepository.findByActiveTrue(pageable)
                .map(this::convertToDto);
    }

    /**
     * Get school by ID with caching.
     */
    @Cacheable(value = "schools", key = "#id")
    public SchoolDto getSchoolById(Long id) {
        School school = schoolRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("School", "id", id));
        return convertToDto(school);
    }

    /**
     * Create a new school.
     */
    @Transactional
    @CacheEvict(value = "schools", allEntries = true)
    public SchoolDto createSchool(SchoolDto schoolDto) {
        validateCodeAvailable(schoolDto.getCode(), null);
        School school = convertToEntity(schoolDto);
        School savedSchool = schoolRepository.save(school);
        return convertToDto(savedSchool);
    }

    /**
     * Update an existing school.
     */
    @Transactional
    @CacheEvict(value = "schools", allEntries = true)
    public SchoolDto updateSchool(Long id, SchoolDto schoolDto) {
        School school = schoolRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("School", "id", id));

        validateCodeAvailable(schoolDto.getCode(), id);
        school.setCode(normalizeCode(schoolDto.getCode()));
        school.setDistrict(trimOptional(schoolDto.getDistrict()));
        school.setName(schoolDto.getName());
        school.setAddress(schoolDto.getAddress());
        school.setCity(schoolDto.getCity());
        school.setState(schoolDto.getState());
        school.setZipCode(schoolDto.getZipCode());
        school.setCountry(schoolDto.getCountry());
        school.setPhone(schoolDto.getPhone());
        school.setEmail(schoolDto.getEmail());
        school.setWebsite(schoolDto.getWebsite());
        school.setDescription(schoolDto.getDescription());
        school.setEstablishedYear(schoolDto.getEstablishedYear());
        school.setStudentCapacity(schoolDto.getStudentCapacity());

        School updatedSchool = schoolRepository.save(school);
        return convertToDto(updatedSchool);
    }

    /**
     * Delete a school (soft delete by setting active to false).
     */
    @Transactional
    @CacheEvict(value = "schools", allEntries = true)
    public void deleteSchool(Long id) {
        School school = schoolRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("School", "id", id));
        school.setActive(false);
        schoolRepository.save(school);
    }

    private SchoolDto convertToDto(School school) {
        SchoolDto dto = new SchoolDto();
        dto.setId(school.getId());
        dto.setCode(school.getCode());
        dto.setDistrict(school.getDistrict());
        dto.setName(school.getName());
        dto.setAddress(school.getAddress());
        dto.setCity(school.getCity());
        dto.setState(school.getState());
        dto.setZipCode(school.getZipCode());
        dto.setCountry(school.getCountry());
        dto.setPhone(school.getPhone());
        dto.setEmail(school.getEmail());
        dto.setWebsite(school.getWebsite());
        dto.setDescription(school.getDescription());
        dto.setActive(school.getActive());
        dto.setEstablishedYear(school.getEstablishedYear());
        dto.setStudentCapacity(school.getStudentCapacity());
        return dto;
    }

    private School convertToEntity(SchoolDto dto) {
        School school = new School();
        school.setCode(normalizeCode(dto.getCode()));
        school.setDistrict(trimOptional(dto.getDistrict()));
        school.setName(dto.getName());
        school.setAddress(dto.getAddress());
        school.setCity(dto.getCity());
        school.setState(dto.getState());
        school.setZipCode(dto.getZipCode());
        school.setCountry(dto.getCountry());
        school.setPhone(dto.getPhone());
        school.setEmail(dto.getEmail());
        school.setWebsite(dto.getWebsite());
        school.setDescription(dto.getDescription());
        school.setActive(true);
        school.setEstablishedYear(dto.getEstablishedYear());
        school.setStudentCapacity(dto.getStudentCapacity());
        return school;
    }

    @Transactional(readOnly = true)
    public List<SchoolResponseDTO> getSchoolsByCity(String city) {
        return schoolRepository.findByCityIgnoreCaseAndActiveTrueOrderByNameAscIdAsc(
                requireLookup(city, "city", 100)).stream().map(this::convertToResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<SchoolResponseDTO> getSchoolsByState(String state) {
        return schoolRepository.findByStateIgnoreCaseAndActiveTrueOrderByNameAscIdAsc(
                requireLookup(state, "state", 100)).stream().map(this::convertToResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<SchoolResponseDTO> getSchoolsByDistrict(String district) {
        return schoolRepository.findByDistrictIgnoreCaseAndActiveTrueOrderByNameAscIdAsc(
                requireLookup(district, "district", 100)).stream().map(this::convertToResponse).toList();
    }

    @Transactional(readOnly = true)
    public List<SchoolResponseDTO> searchSchools(String keyword) {
        return schoolRepository.findByNameContainingIgnoreCaseAndActiveTrueOrderByNameAscIdAsc(
                requireLookup(keyword, "keyword", 200)).stream().map(this::convertToResponse).toList();
    }

    @Transactional(readOnly = true)
    public SchoolResponseDTO getSchoolByCode(String code) {
        String value = requireLookup(code, "code", 50);
        return schoolRepository.findByCodeIgnoreCaseAndActiveTrue(value)
                .map(this::convertToResponse)
                .orElseThrow(() -> new ResourceNotFoundException("School", "code", value));
    }

    private String requireLookup(String value, String field, int maxLength) {
        if (value == null || value.isBlank() || value.trim().length() > maxLength) {
            throw new BadRequestException(field + " must contain 1 to " + maxLength + " characters");
        }
        return value.trim();
    }

    private String trimOptional(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String normalizeCode(String code) {
        String value = trimOptional(code);
        return value == null ? null : value.toUpperCase(Locale.ROOT);
    }

    private void validateCodeAvailable(String code, Long currentId) {
        String normalized = normalizeCode(code);
        if (normalized == null) return;
        schoolRepository.findByCodeIgnoreCase(normalized).ifPresent(existing -> {
            if (!Objects.equals(existing.getId(), currentId)) {
                throw new BadRequestException("School code already exists: " + normalized);
            }
        });
    }

    private SchoolResponseDTO convertToResponse(School school) {
        SchoolResponseDTO dto = new SchoolResponseDTO();
        dto.setId(school.getId());
        dto.setName(school.getName());
        dto.setCode(school.getCode());
        dto.setAddress(school.getAddress());
        dto.setCity(school.getCity());
        dto.setState(school.getState());
        dto.setDistrict(school.getDistrict());
        dto.setZipCode(school.getZipCode());
        dto.setContactEmail(school.getEmail());
        dto.setContactPhone(school.getPhone());
        dto.setWebsite(school.getWebsite());
        dto.setEstablishedYear(school.getEstablishedYear());
        dto.setDescription(school.getDescription());
        dto.setActive(school.getActive());
        dto.setCreatedAt(school.getCreatedAt());
        dto.setUpdatedAt(school.getUpdatedAt());
        return dto;
    }
}
