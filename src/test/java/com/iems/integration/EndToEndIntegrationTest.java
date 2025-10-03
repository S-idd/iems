package com.iems.integration;

import java.math.BigDecimal;

import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.hasSize;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.iems.model.dto.AccessibilityReportDto;
import com.iems.model.dto.AuthRequest;
import com.iems.model.dto.RegisterRequest;
import com.iems.model.dto.ScholarshipDto;
import com.iems.model.dto.SchoolDto;
import com.iems.model.enums.DisabilityType;
import com.iems.model.enums.UserRole;

/**
 * Complete end-to-end integration tests for IEMS workflows.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class EndToEndIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    private static String adminToken;
    private static Long schoolId;
    private static Long studentId;

    @Test
    @Order(1)
    public void test01_RegisterAdminUser() throws Exception {
        RegisterRequest request = new RegisterRequest();
        request.setUsername("admin");
        request.setPassword("admin123");
        request.setEmail("admin@test.com");
        request.setFirstName("Admin");
        request.setLastName("User");
        request.setRole(UserRole.ADMIN);

        mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("admin"))
                .andExpect(jsonPath("$.role").value("ADMIN"));
    }

    @Test
    @Order(2)
    public void test02_LoginAdmin() throws Exception {
        AuthRequest request = new AuthRequest();
        request.setUsername("admin");
        request.setPassword("admin123");

        MvcResult result = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").exists())
                .andExpect(jsonPath("$.user.username").value("admin"))
                .andReturn();

        String response = result.getResponse().getContentAsString();
        adminToken = objectMapper.readTree(response).get("accessToken").asText();
        Assertions.assertNotNull(adminToken);
    }

    @Test
    @Order(3)
    public void test03_CreateSchool() throws Exception {
        SchoolDto school = new SchoolDto();
        school.setName("Test Integration School");
        school.setAddress("123 Test Street");
        school.setCity("Test City");
        school.setEmail("school@test.com");
        school.setPhone("555-0123");

        MvcResult result = mockMvc.perform(post("/api/schools")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(school)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.name").value("Test Integration School"))
                .andExpect(jsonPath("$.id").exists())
                .andReturn();

        String response = result.getResponse().getContentAsString();
        schoolId = objectMapper.readTree(response).get("id").asLong();
        Assertions.assertNotNull(schoolId);
    }

    @Test
    @Order(4)
    public void test04_GetAllSchools() throws Exception {
        mockMvc.perform(get("/api/schools/active")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(greaterThan(0))))
                .andExpect(jsonPath("$[0].name").value("Test Integration School"));
    }

    @Test
    @Order(5)
    public void test05_RegisterStudent() throws Exception {
        RegisterRequest request = new RegisterRequest();
        request.setUsername("student1");
        request.setPassword("student123");
        request.setEmail("student1@test.com");
        request.setFirstName("John");
        request.setLastName("Doe");
        request.setRole(UserRole.STUDENT);
        request.setSchoolId(schoolId);

        MvcResult result = mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("student1"))
                .andReturn();

        String response = result.getResponse().getContentAsString();
        studentId = objectMapper.readTree(response).get("id").asLong();
    }

    @Test
    @Order(6)
    public void test06_CreateAccessibilityReport() throws Exception {
        AccessibilityReportDto report = new AccessibilityReportDto();
        report.setStudentId(studentId);
        report.setSchoolId(schoolId);
        report.setTitle("Wheelchair Access Issue");
        report.setDescription("Ramp is too steep at building entrance");
        report.setRelatedDisability(DisabilityType.PHYSICAL);
        report.setSeverity("HIGH");
        report.setLocation("Main Building Entrance");

        mockMvc.perform(post("/api/accessibility/reports")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(report)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Wheelchair Access Issue"))
                .andExpect(jsonPath("$.severity").value("HIGH"));
    }

    @Test
    @Order(7)
    public void test07_CreateScholarshipApplication() throws Exception {
        ScholarshipDto scholarship = new ScholarshipDto();
        scholarship.setScholarshipName("Merit Scholarship 2024");
        scholarship.setStudentId(studentId);
        scholarship.setAmountRequested(new BigDecimal("5000.00"));
        scholarship.setPurpose("Tuition and books");
        scholarship.setJustification("High academic performance");

        mockMvc.perform(post("/api/scholarships")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(scholarship)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.scholarshipName").value("Merit Scholarship 2024"))
                .andExpect(jsonPath("$.status").value("PENDING"));
    }

    @Test
    @Order(8)
    public void test08_GetScholarshipStatistics() throws Exception {
        mockMvc.perform(get("/api/scholarships/statistics")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalApplications").exists())
                .andExpect(jsonPath("$.pendingApplications").exists());
    }

    @Test
    @Order(9)
    public void test09_GetAccessibilityStatistics() throws Exception {
        mockMvc.perform(get("/api/accessibility/statistics/school/" + schoolId)
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalReports").exists());
    }

    @Test
    @Order(10)
    public void test10_Logout() throws Exception {
        mockMvc.perform(post("/api/auth/logout")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isNoContent());
    }
}