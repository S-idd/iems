package com.iems.service;

import com.iems.controller.SchoolController;
import com.iems.exception.GlobalExceptionHandler;
import com.iems.model.entity.School;
import com.iems.repository.SchoolRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@DataJpaTest(properties = {"spring.flyway.enabled=false", "spring.jpa.hibernate.ddl-auto=create-drop",
        "spring.sql.init.mode=never", "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"})
@Import(SchoolService.class)
class SchoolEndpointsIntegrationTest {
    @Autowired SchoolRepository repository;
    @Autowired SchoolService service;
    MockMvc mvc;
    School school;

    @BeforeEach
    void setUp() {
        SchoolController controller = new SchoolController();
        ReflectionTestUtils.setField(controller, "schoolService", service);
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new GlobalExceptionHandler()).build();
        school = save("Inclusive Academy", "INC01", true);
        save("Inclusive Closed", "OLD01", false);
        School other = save("Other Academy", "OTHER01", true);
        other.setCity("Mysuru"); other.setState("Kerala"); other.setDistrict("Other");
        repository.saveAndFlush(other);
    }

    private School save(String name, String code, boolean active) {
        School value = new School(name, "Main Street", "school@example.test");
        value.setCity("Bengaluru"); value.setState("Karnataka");
        value.setDistrict("Bengaluru Urban"); value.setCode(code); value.setActive(active);
        value.setPhone("1234567890");
        return repository.saveAndFlush(value);
    }

    @Test
    void locationFiltersAreCaseInsensitiveAndExcludeInactiveSchools() throws Exception {
        for (String path : new String[]{"/city/bEnGaLuRu", "/state/karnataka", "/district/bengaluru urban"}) {
            mvc.perform(get("/api/schools" + path)).andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.length()").value(1))
                    .andExpect(jsonPath("$.data[0].code").value("INC01"))
                    .andExpect(jsonPath("$.data[0].contactEmail").value("school@example.test"));
        }
    }

    @Test
    void searchMatchesNameSubstringAndEscapesWildcards() throws Exception {
        mvc.perform(get("/api/schools/search").param("keyword", "  INCLUSIVE  "))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.length()").value(1));
        for (String keyword : new String[]{"%", "_", "not present"}) {
            mvc.perform(get("/api/schools/search").param("keyword", keyword))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.data").isEmpty());
        }
    }

    @Test
    void codeLookupMapsFieldsAndMissingOrInactiveCodeReturns404() throws Exception {
        mvc.perform(get("/api/schools/code/inc01"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.id").value(school.getId()))
                .andExpect(jsonPath("$.data.district").value("Bengaluru Urban"))
                .andExpect(jsonPath("$.data.contactPhone").value("1234567890"))
                .andExpect(jsonPath("$.data.fullAddress").value("Main Street, Bengaluru, Bengaluru Urban, Karnataka"));
        for (String code : new String[]{"unknown", "OLD01"}) {
            mvc.perform(get("/api/schools/code/" + code))
                    .andExpect(status().isNotFound()).andExpect(jsonPath("$.status").value(404));
        }
    }

    @Test
    void invalidSearchReturns400RatherThan500() throws Exception {
        mvc.perform(get("/api/schools/search")).andExpect(status().isBadRequest());
        for (String keyword : new String[]{"", "   ", "x".repeat(201)}) {
            mvc.perform(get("/api/schools/search").param("keyword", keyword))
                    .andExpect(status().isBadRequest()).andExpect(jsonPath("$.status").value(400));
        }
    }

    @Test
    void createAndUpdatePersistLookupFieldsAndRejectDuplicateCode() throws Exception {
        mvc.perform(post("/api/schools").contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"name":"New School","code":"new01","district":"New District"}
                    """))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.code").value("NEW01"));
        assertThat(repository.findByCodeIgnoreCase("new01")).isPresent();
        mvc.perform(put("/api/schools/" + school.getId()).contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"name":"Updated School","code":"inc01","district":"Updated District"}
                    """))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.district").value("Updated District"));
        mvc.perform(get("/api/schools/district/Updated District"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data[0].code").value("INC01"));
        mvc.perform(post("/api/schools").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Duplicate\",\"code\":\"inc01\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void existingRequestsWithoutCodeStillWorkAndInvalidCodeIsRejected() throws Exception {
        mvc.perform(post("/api/schools").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Legacy School\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.name").value("Legacy School"));
        mvc.perform(post("/api/schools").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Bad Code\",\"code\":\"!bad\"}"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.code").exists());
    }
    @Test
    void softDeleteRemovesSchoolFromLookupsAndKeepsCodeReserved() throws Exception {
        mvc.perform(delete("/api/schools/" + school.getId())).andExpect(status().isOk());
        mvc.perform(get("/api/schools/city/Bengaluru"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data").isEmpty());
        mvc.perform(get("/api/schools/code/INC01")).andExpect(status().isNotFound());
        mvc.perform(post("/api/schools").contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Reused code\",\"code\":\"inc01\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void updateCannotTakeAnotherSchoolsCodeAndMalformedJsonReturns400() throws Exception {
        mvc.perform(put("/api/schools/" + school.getId()).contentType(MediaType.APPLICATION_JSON)
                .content("{\"name\":\"Duplicate code\",\"code\":\"other01\"}"))
                .andExpect(status().isBadRequest());
        assertThat(repository.findById(school.getId()).orElseThrow().getCode()).isEqualTo("INC01");
        mvc.perform(post("/api/schools").contentType(MediaType.APPLICATION_JSON).content("{"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.status").value(400));
    }

}
