package com.iems.controller;

import java.util.List;
import java.util.Map;

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

import com.iems.model.dto.ApiResponse;
import com.iems.model.dto.StudentDto;
import com.iems.service.StudentService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/students")
public class StudentController {

    @Autowired
    private StudentService studentService;

    // Get all students with pagination
    @GetMapping
    public ResponseEntity<ApiResponse<Page<StudentDto>>> getAllStudents(Pageable pageable) {
        Page<StudentDto> students = studentService.getAllStudents(pageable);
        return ResponseEntity.ok(ApiResponse.success("Students retrieved", students));
    }

    // Get a student by ID
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<StudentDto>> getStudentById(@PathVariable Long id) {
        StudentDto student = studentService.getStudentById(id);
        return ResponseEntity.ok(ApiResponse.success("Student retrieved", student));
    }

    // Get a student by user ID
    @GetMapping("/user/{userId}")
    public ResponseEntity<ApiResponse<StudentDto>> getStudentByUserId(@PathVariable Long userId) {
        StudentDto student = studentService.getStudentByUserId(userId);
        return ResponseEntity.ok(ApiResponse.success("Student retrieved by user ID", student));
    }

    // Get a student by student number
    @GetMapping("/number/{studentNumber}")
    public ResponseEntity<ApiResponse<StudentDto>> getStudentByNumber(@PathVariable String studentNumber) {
        StudentDto student = studentService.getStudentByNumber(studentNumber);
        return ResponseEntity.ok(ApiResponse.success("Student retrieved by number", student));
    }

    // Get students by school ID
    @GetMapping("/school/{schoolId}")
    public ResponseEntity<ApiResponse<List<StudentDto>>> getStudentsBySchool(@PathVariable Long schoolId) {
        List<StudentDto> students = studentService.getStudentsBySchool(schoolId);
        return ResponseEntity.ok(ApiResponse.success("Students by school retrieved", students));
    }

    // Get students with disabilities
    @GetMapping("/disabilities")
    public ResponseEntity<ApiResponse<List<StudentDto>>> getStudentsWithDisabilities() {
        List<StudentDto> students = studentService.getStudentsWithDisabilities();
        return ResponseEntity.ok(ApiResponse.success("Students with disabilities retrieved", students));
    }

    // Create a new student
    @PostMapping
    public ResponseEntity<ApiResponse<StudentDto>> createStudent(@Valid @RequestBody StudentDto studentDto) {
        StudentDto createdStudent = studentService.createStudent(studentDto);
        return ResponseEntity.ok(ApiResponse.success("Student created successfully", createdStudent));
    }

    // Update a student
    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<StudentDto>> updateStudent(@PathVariable Long id,
                                                                 @Valid @RequestBody StudentDto studentDto) {
        StudentDto updatedStudent = studentService.updateStudent(id, studentDto);
        return ResponseEntity.ok(ApiResponse.success("Student updated successfully", updatedStudent));
    }

    // Delete a student
    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteStudent(@PathVariable Long id) {
        studentService.deleteStudent(id);
        return ResponseEntity.ok(ApiResponse.success("Student deleted successfully", null));
    }

    // Get student statistics by school
    @GetMapping("/statistics/{schoolId}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getStudentStatistics(@PathVariable Long schoolId) {
        Map<String, Object> stats = studentService.getStudentStatistics(schoolId);
        return ResponseEntity.ok(ApiResponse.success("Student statistics retrieved", stats));
    }
}
