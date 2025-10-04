package com.iems.model.dto;

import jakarta.validation.constraints.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SchoolRequestDTO {

    @NotBlank(message = "School name is required")
    @Size(min = 3, max = 200, message = "School name must be between 3 and 200 characters")
    private String name;

    @NotBlank(message = "School code is required")
    @Size(min = 3, max = 50, message = "School code must be between 3 and 50 characters")
    @Pattern(regexp = "^[A-Z0-9]+$", message = "School code must contain only uppercase letters and numbers")
    private String code;

    @NotBlank(message = "School type is required")
    @Pattern(regexp = "PRIMARY|MIDDLE_SCHOOL|HIGH_SCHOOL|SENIOR_SECONDARY|COLLEGE|UNIVERSITY", 
             message = "Invalid school type")
    private String type;

    @NotBlank(message = "Address is required")
    @Size(max = 500, message = "Address must not exceed 500 characters")
    private String address;

    @NotBlank(message = "City is required")
    @Size(max = 100, message = "City must not exceed 100 characters")
    private String city;

    @NotBlank(message = "State is required")
    @Size(max = 100, message = "State must not exceed 100 characters")
    private String state;

    @NotBlank(message = "ZIP code is required")
    @Pattern(regexp = "^[0-9]{5,10}$", message = "Invalid ZIP code format")
    private String zipCode;

    @Size(max = 100, message = "District must not exceed 100 characters")
    private String district;

    @NotBlank(message = "Contact email is required")
    @Email(message = "Invalid email format")
    private String contactEmail;

    @NotBlank(message = "Contact phone is required")
    @Pattern(regexp = "^\\+?[1-9]\\d{1,14}$", message = "Invalid phone number format")
    private String contactPhone;

    @Pattern(regexp = "^(https?://)?(www\\.)?[a-zA-Z0-9-]+(\\.[a-zA-Z]{2,})+(/.*)?$", 
             message = "Invalid website URL", 
             flags = Pattern.Flag.CASE_INSENSITIVE)
    private String website;

    @Size(max = 100, message = "Principal name must not exceed 100 characters")
    private String principalName;

    @Email(message = "Invalid principal email format")
    private String principalEmail;

    @Pattern(regexp = "^\\+?[1-9]\\d{1,14}$", message = "Invalid principal phone format")
    private String principalPhone;

    @Min(value = 1900, message = "Established year must be after 1900")
    @Max(value = 2100, message = "Established year must be before 2100")
    private Integer establishedYear;

    @Pattern(regexp = "GOVERNMENT|PRIVATE|AIDED|AUTONOMOUS", 
             message = "Invalid affiliation type")
    private String affiliationType;

    @Size(max = 200, message = "Affiliation body must not exceed 200 characters")
    private String affiliationBody;

    @Size(max = 100, message = "Affiliation number must not exceed 100 characters")
    private String affiliationNumber;

    @Min(value = 0, message = "Total students cannot be negative")
    private Integer totalStudents;

    @Min(value = 0, message = "Total faculty cannot be negative")
    private Integer totalFaculty;

    @Size(max = 1000, message = "Description must not exceed 1000 characters")
    private String description;

    private Boolean active = true;

    @Size(max = 500, message = "Facilities must not exceed 500 characters")
    private String facilities;

    @Pattern(regexp = "CBSE|ICSE|STATE_BOARD|IB|IGCSE", 
             message = "Invalid board type")
    private String board;

    private Boolean hasLibrary;

    private Boolean hasLaboratory;

    private Boolean hasSportsComplex;

    private Boolean hasHostel;

    private Boolean hasTransport;

    @Size(max = 500, message = "Remarks must not exceed 500 characters")
    private String remarks;
}