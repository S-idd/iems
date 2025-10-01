package com.iems.model.dto;

import java.time.LocalDate;
import java.util.Set;

import com.iems.model.enums.DisabilityType;

public class StudentDto {
    private Long id;
    private Long userId;
    private String username;
    private String studentNumber;
    private String firstName;
    private String lastName;
    private String email;
    private LocalDate dateOfBirth;
    private String gender;
    private String emergencyContactName;
    private String emergencyContactPhone;
    private Boolean hasDisability;
    private Set<DisabilityType> disabilities;
    private String accommodationsNeeded;
    private String assistiveTechnology;
    private LocalDate enrollmentDate;
    private String major;
    private Integer currentYear;
    private Double gpa;

    // Getters and Setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getStudentNumber() {
        return studentNumber;
    }

    public void setStudentNumber(String studentNumber) {
        this.studentNumber = studentNumber;
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public LocalDate getDateOfBirth() {
        return dateOfBirth;
    }

    public void setDateOfBirth(LocalDate dateOfBirth) {
        this.dateOfBirth = dateOfBirth;
    }

    public String getGender() {
        return gender;
    }

    public void setGender(String gender) {
        this.gender = gender;
    }

    public String getEmergencyContactName() {
        return emergencyContactName;
    }

    public void setEmergencyContactName(String emergencyContactName) {
        this.emergencyContactName = emergencyContactName;
    }

    public String getEmergencyContactPhone() {
        return emergencyContactPhone;
    }

    public void setEmergencyContactPhone(String emergencyContactPhone) {
        this.emergencyContactPhone = emergencyContactPhone;
    }

    public Boolean getHasDisability() {
        return hasDisability;
    }

    public void setHasDisability(Boolean hasDisability) {
        this.hasDisability = hasDisability;
    }

    public Set<DisabilityType> getDisabilities() {
        return disabilities;
    }

    public void setDisabilities(Set<DisabilityType> disabilities) {
        this.disabilities = disabilities;
    }

    public String getAccommodationsNeeded() {
        return accommodationsNeeded;
    }

    public void setAccommodationsNeeded(String accommodationsNeeded) {
        this.accommodationsNeeded = accommodationsNeeded;
    }

    public String getAssistiveTechnology() {
        return assistiveTechnology;
    }

    public void setAssistiveTechnology(String assistiveTechnology) {
        this.assistiveTechnology = assistiveTechnology;
    }

    public LocalDate getEnrollmentDate() {
        return enrollmentDate;
    }

    public void setEnrollmentDate(LocalDate enrollmentDate) {
        this.enrollmentDate = enrollmentDate;
    }

    public String getMajor() {
        return major;
    }

    public void setMajor(String major) {
        this.major = major;
    }

    public Integer getCurrentYear() {
        return currentYear;
    }

    public void setCurrentYear(Integer currentYear) {
        this.currentYear = currentYear;
    }

    public Double getGpa() {
        return gpa;
    }

    public void setGpa(Double gpa) {
        this.gpa = gpa;
    }
}