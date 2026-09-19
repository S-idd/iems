package com.iems.model.dto;

import java.time.LocalDateTime;
import java.util.stream.Stream;
import java.util.stream.Collectors;

public class SchoolResponseDTO {

    private Long id;

    private String name;

    private String code;

    private String type;

    private String address;

    private String city;

    private String state;

    private String zipCode;

    private String district;

    private String contactEmail;

    private String contactPhone;

    private String website;

    private String principalName;

    private String principalEmail;

    private String principalPhone;

    private Integer establishedYear;

    private String affiliationType;

    private String affiliationBody;

    private String affiliationNumber;

    private Integer totalStudents;

    private Integer totalFaculty;

    private String description;

    private Boolean active;

    private String facilities;

    private String board;

    private Boolean hasLibrary;

    private Boolean hasLaboratory;

    private Boolean hasSportsComplex;

    private Boolean hasHostel;

    private Boolean hasTransport;

    private String remarks;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    // Additional computed fields
    private Long scholarshipCount;

    private Long studentCount;

    private String fullAddress;

    // Constructor for computed full address
    public String getFullAddress() {
        return Stream.of(address, city, district, state, zipCode)
                .filter(value -> value != null && !value.isBlank())
                .collect(Collectors.joining(", "));
    }

    public SchoolResponseDTO() {
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public String getZipCode() {
        return zipCode;
    }

    public void setZipCode(String zipCode) {
        this.zipCode = zipCode;
    }

    public String getDistrict() {
        return district;
    }

    public void setDistrict(String district) {
        this.district = district;
    }

    public String getContactEmail() {
        return contactEmail;
    }

    public void setContactEmail(String contactEmail) {
        this.contactEmail = contactEmail;
    }

    public String getContactPhone() {
        return contactPhone;
    }

    public void setContactPhone(String contactPhone) {
        this.contactPhone = contactPhone;
    }

    public String getWebsite() {
        return website;
    }

    public void setWebsite(String website) {
        this.website = website;
    }

    public String getPrincipalName() {
        return principalName;
    }

    public void setPrincipalName(String principalName) {
        this.principalName = principalName;
    }

    public String getPrincipalEmail() {
        return principalEmail;
    }

    public void setPrincipalEmail(String principalEmail) {
        this.principalEmail = principalEmail;
    }

    public String getPrincipalPhone() {
        return principalPhone;
    }

    public void setPrincipalPhone(String principalPhone) {
        this.principalPhone = principalPhone;
    }

    public Integer getEstablishedYear() {
        return establishedYear;
    }

    public void setEstablishedYear(Integer establishedYear) {
        this.establishedYear = establishedYear;
    }

    public String getAffiliationType() {
        return affiliationType;
    }

    public void setAffiliationType(String affiliationType) {
        this.affiliationType = affiliationType;
    }

    public String getAffiliationBody() {
        return affiliationBody;
    }

    public void setAffiliationBody(String affiliationBody) {
        this.affiliationBody = affiliationBody;
    }

    public String getAffiliationNumber() {
        return affiliationNumber;
    }

    public void setAffiliationNumber(String affiliationNumber) {
        this.affiliationNumber = affiliationNumber;
    }

    public Integer getTotalStudents() {
        return totalStudents;
    }

    public void setTotalStudents(Integer totalStudents) {
        this.totalStudents = totalStudents;
    }

    public Integer getTotalFaculty() {
        return totalFaculty;
    }

    public void setTotalFaculty(Integer totalFaculty) {
        this.totalFaculty = totalFaculty;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Boolean getActive() {
        return active;
    }

    public void setActive(Boolean active) {
        this.active = active;
    }

    public String getFacilities() {
        return facilities;
    }

    public void setFacilities(String facilities) {
        this.facilities = facilities;
    }

    public String getBoard() {
        return board;
    }

    public void setBoard(String board) {
        this.board = board;
    }

    public Boolean getHasLibrary() {
        return hasLibrary;
    }

    public void setHasLibrary(Boolean hasLibrary) {
        this.hasLibrary = hasLibrary;
    }

    public Boolean getHasLaboratory() {
        return hasLaboratory;
    }

    public void setHasLaboratory(Boolean hasLaboratory) {
        this.hasLaboratory = hasLaboratory;
    }

    public Boolean getHasSportsComplex() {
        return hasSportsComplex;
    }

    public void setHasSportsComplex(Boolean hasSportsComplex) {
        this.hasSportsComplex = hasSportsComplex;
    }

    public Boolean getHasHostel() {
        return hasHostel;
    }

    public void setHasHostel(Boolean hasHostel) {
        this.hasHostel = hasHostel;
    }

    public Boolean getHasTransport() {
        return hasTransport;
    }

    public void setHasTransport(Boolean hasTransport) {
        this.hasTransport = hasTransport;
    }

    public String getRemarks() {
        return remarks;
    }

    public void setRemarks(String remarks) {
        this.remarks = remarks;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public Long getScholarshipCount() {
        return scholarshipCount;
    }

    public void setScholarshipCount(Long scholarshipCount) {
        this.scholarshipCount = scholarshipCount;
    }

    public Long getStudentCount() {
        return studentCount;
    }

    public void setStudentCount(Long studentCount) {
        this.studentCount = studentCount;
    }

    public void setFullAddress(String fullAddress) {
        this.fullAddress = fullAddress;
    }
}
