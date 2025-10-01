package com.iems.service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.iems.exception.BadRequestException;
import com.iems.exception.ResourceNotFoundException;
import com.iems.model.dto.StudentDto;
import com.iems.model.entity.StudentProfile;
import com.iems.model.entity.User;
import com.iems.repository.StudentRepository;
import com.iems.repository.UserRepository;

/**
 * Service for managing student profiles and related operations.
 */
@Service
public class StudentService {

    @Autowired
    private StudentRepository studentRepository;

    @Autowired
    private UserRepository userRepository;

    public Page<StudentDto> getAllStudents(Pageable pageable) {
        return studentRepository.findAll(pageable)
                .map(this::convertToDto);
    }

    @Cacheable(value = "students", key = "#id")
    public StudentDto getStudentById(Long id) {
        StudentProfile student = studentRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Student", "id", id));
        return convertToDto(student);
    }

    public List<StudentDto> getStudentsBySchool(Long schoolId) {
        return studentRepository.findBySchoolId(schoolId).stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    public StudentDto getStudentByUserId(Long userId) {
        StudentProfile student = studentRepository.findByUserId(userId)
                .orElseThrow(() -> new ResourceNotFoundException("Student", "userId", userId));
        return convertToDto(student);
    }

    public StudentDto getStudentByNumber(String studentNumber) {
        StudentProfile student = studentRepository.findByStudentNumber(studentNumber)
                .orElseThrow(() -> new ResourceNotFoundException("Student", "studentNumber", studentNumber));
        return convertToDto(student);
    }

    public List<StudentDto> getStudentsWithDisabilities() {
        return studentRepository.findByHasDisabilityTrue().stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    @Transactional
    @CacheEvict(value = "students", allEntries = true)
    public StudentDto createStudent(StudentDto dto) {
        // Validate user exists
        User user = userRepository.findById(dto.getUserId())
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", dto.getUserId()));

        // Check if student profile already exists for this user
        if (studentRepository.findByUserId(user.getId()).isPresent()) {
            throw new BadRequestException("Student profile already exists for this user");
        }

        // Check if student number is unique
        if (dto.getStudentNumber() != null && 
            studentRepository.findByStudentNumber(dto.getStudentNumber()).isPresent()) {
            throw new BadRequestException("Student number already exists");
        }

        StudentProfile student = new StudentProfile();
        student.setUser(user);
        student.setStudentNumber(dto.getStudentNumber());
        student.setDateOfBirth(dto.getDateOfBirth());
        student.setGender(dto.getGender());
        student.setEmergencyContactName(dto.getEmergencyContactName());
        student.setEmergencyContactPhone(dto.getEmergencyContactPhone());
        student.setHasDisability(dto.getHasDisability() != null ? dto.getHasDisability() : false);
        
        if (dto.getDisabilities() != null && !dto.getDisabilities().isEmpty()) {
            student.setDisabilities(dto.getDisabilities());
            student.setHasDisability(true);
        }
        
        student.setAccommodationsNeeded(dto.getAccommodationsNeeded());
        student.setAssistiveTechnology(dto.getAssistiveTechnology());
        student.setEnrollmentDate(dto.getEnrollmentDate());
        student.setMajor(dto.getMajor());
        student.setCurrentYear(dto.getCurrentYear());
        // StudentProfile.gpa is BigDecimal, dto.gpa is Double -> convert safely
        if (dto.getGpa() != null) {
            student.setGpa(java.math.BigDecimal.valueOf(dto.getGpa()));
        } else {
            student.setGpa(null);
        }

        StudentProfile saved = studentRepository.save(student);
        return convertToDto(saved);
    }

    @Transactional
    @CacheEvict(value = "students", allEntries = true)
    public StudentDto updateStudent(Long id, StudentDto dto) {
        StudentProfile student = studentRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Student", "id", id));

        // Update fields
        if (dto.getDateOfBirth() != null) {
            student.setDateOfBirth(dto.getDateOfBirth());
        }
        if (dto.getGender() != null) {
            student.setGender(dto.getGender());
        }
        if (dto.getEmergencyContactName() != null) {
            student.setEmergencyContactName(dto.getEmergencyContactName());
        }
        if (dto.getEmergencyContactPhone() != null) {
            student.setEmergencyContactPhone(dto.getEmergencyContactPhone());
        }
        
        // Update disability information
        if (dto.getHasDisability() != null) {
            student.setHasDisability(dto.getHasDisability());
        }
        if (dto.getDisabilities() != null) {
            student.setDisabilities(dto.getDisabilities());
            if (!dto.getDisabilities().isEmpty()) {
                student.setHasDisability(true);
            }
        }
        if (dto.getAccommodationsNeeded() != null) {
            student.setAccommodationsNeeded(dto.getAccommodationsNeeded());
        }
        if (dto.getAssistiveTechnology() != null) {
            student.setAssistiveTechnology(dto.getAssistiveTechnology());
        }
        
        // Update academic information
        if (dto.getMajor() != null) {
            student.setMajor(dto.getMajor());
        }
        if (dto.getCurrentYear() != null) {
            student.setCurrentYear(dto.getCurrentYear());
        }
        if (dto.getGpa() != null) {
            student.setGpa(java.math.BigDecimal.valueOf(dto.getGpa()));
        }

        StudentProfile updated = studentRepository.save(student);
        return convertToDto(updated);
    }

    @Transactional
    @CacheEvict(value = "students", allEntries = true)
    public void deleteStudent(Long id) {
        StudentProfile student = studentRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Student", "id", id));
        studentRepository.delete(student);
    }

    public Map<String, Object> getStudentStatistics(Long schoolId) {
        Map<String, Object> stats = new HashMap<>();
        
        List<StudentProfile> schoolStudents = studentRepository.findBySchoolId(schoolId);
        
        stats.put("totalStudents", (long) schoolStudents.size());
        stats.put("studentsWithDisabilities", 
            schoolStudents.stream().filter(s -> s.getHasDisability() != null && s.getHasDisability()).count());
        
    // Calculate average GPA (StudentProfile.gpa is BigDecimal)
    double avgGpa = schoolStudents.stream()
        .filter(s -> s.getGpa() != null)
        .map(s -> s.getGpa().doubleValue())
        .mapToDouble(Double::doubleValue)
        .average()
        .orElse(0.0);
    stats.put("averageGpa", Math.round(avgGpa * 100.0) / 100.0);
        
        // Count by year
        Map<Integer, Long> byYear = schoolStudents.stream()
                .filter(s -> s.getCurrentYear() != null)
                .collect(Collectors.groupingBy(StudentProfile::getCurrentYear, Collectors.counting()));
        stats.put("studentsByYear", byYear);
        
        // Count by major
        Map<String, Long> byMajor = schoolStudents.stream()
                .filter(s -> s.getMajor() != null && !s.getMajor().isEmpty())
                .collect(Collectors.groupingBy(StudentProfile::getMajor, Collectors.counting()));
        stats.put("studentsByMajor", byMajor);
        
        return stats;
    }

    private StudentDto convertToDto(StudentProfile student) {
        StudentDto dto = new StudentDto();
        dto.setId(student.getId());
        dto.setUserId(student.getUser().getId());
        dto.setUsername(student.getUser().getUsername());
        dto.setStudentNumber(student.getStudentNumber());
        dto.setFirstName(student.getUser().getFirstName());
        dto.setLastName(student.getUser().getLastName());
        dto.setEmail(student.getUser().getEmail());
        dto.setDateOfBirth(student.getDateOfBirth());
        dto.setGender(student.getGender());
        dto.setEmergencyContactName(student.getEmergencyContactName());
        dto.setEmergencyContactPhone(student.getEmergencyContactPhone());
        dto.setHasDisability(student.getHasDisability());
        dto.setDisabilities(student.getDisabilities());
        dto.setAccommodationsNeeded(student.getAccommodationsNeeded());
        dto.setAssistiveTechnology(student.getAssistiveTechnology());
        dto.setEnrollmentDate(student.getEnrollmentDate());
        dto.setMajor(student.getMajor());
        dto.setCurrentYear(student.getCurrentYear());
        dto.setGpa(student.getGpa() != null ? student.getGpa().doubleValue() : null);
        return dto;
    }
}