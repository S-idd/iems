package com.iems.service;

import java.util.List;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.iems.exception.ResourceNotFoundException;
import com.iems.model.dto.SchoolDto;
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
}