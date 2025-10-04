package com.iems.model.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
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
        return String.format("%s, %s, %s, %s - %s", 
            address, city, district, state, zipCode);
    }
}