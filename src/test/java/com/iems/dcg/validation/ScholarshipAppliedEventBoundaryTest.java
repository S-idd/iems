package com.iems.dcg.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.ideas.contracts.starter.ContractPayloadValidationException;
import com.ideas.contracts.starter.ContractPayloadValidator;
import com.ideas.contracts.starter.ContractValidationProperties;
import com.iems.kafka.model.ScholarshipEvent;
import com.iems.model.dto.ScholarshipDto;
import com.iems.model.entity.ScholarshipApplication;
import com.iems.model.entity.StudentProfile;
import com.iems.model.entity.User;
import com.iems.model.enums.ScholarshipStatus;
import com.iems.rabbit.producer.TaskProducer;
import com.iems.repository.ScholarshipRepository;
import com.iems.repository.StudentRepository;
import com.iems.service.EventPublisherService;
import com.iems.service.ScholarshipService;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.support.serializer.JsonSerializer;
import org.springframework.test.util.ReflectionTestUtils;

class ScholarshipAppliedEventBoundaryTest {
    private static final Path CONTRACTS = Path.of("runtime-contracts").toAbsolutePath();
    private final ObjectMapper mapper = IemsEventJson.mapper();
    private EventPublisherService publisher;
    private ContractValidationProperties properties;
    private ScholarshipAppliedEventBoundary boundary;

    @BeforeEach
    void setUp() {
        publisher = mock(EventPublisherService.class);
        properties = new ContractValidationProperties();
        properties.setEnabled(true);
        properties.setContractsRoot(CONTRACTS.toString());
        boundary = new ScholarshipAppliedEventBoundary(
                new ContractPayloadValidator(CONTRACTS.toString(), mapper), properties, publisher);
    }

    private ScholarshipEvent realAppliedEvent() {
        ScholarshipEvent event = new ScholarshipEvent();
        event.setScholarshipId(101L);
        event.setStudentId(7L);
        event.setStudentName("Demo Student");
        event.setEventType("APPLIED");
        event.setStatus(ScholarshipStatus.PENDING);
        event.setAmount(new BigDecimal("1500.00"));
        return event;
    }

    @Test
    void realSerializerAndSchemaAlignAndValidEventCrossesPublisherOnce() throws Exception {
        ScholarshipEvent event = realAppliedEvent();
        JsonNode serialized = mapper.valueToTree(event);
        try (JsonSerializer<ScholarshipEvent> kafka = new JsonSerializer<>(IemsEventJson.mapper())) {
            JsonNode kafkaPayload = mapper.readTree(kafka.serialize("iems.events.scholarship", event));
            ObjectNode expected = serialized.deepCopy();
            ObjectNode actual = kafkaPayload.deepCopy();
            assertEquals(0, expected.remove("amount").decimalValue()
                    .compareTo(actual.remove("amount").decimalValue()));
            assertEquals(expected.toString(), actual.toString());
            new ContractPayloadValidator(CONTRACTS.toString(), mapper).validate(
                    ScholarshipAppliedEventBoundary.CONTRACT_ID,
                    ScholarshipAppliedEventBoundary.VERSION, kafkaPayload);
        }
        assertEquals(7, serialized.size());
        assertTrue(serialized.path("amount").isNumber());
        assertTrue(serialized.path("timestamp").isTextual());
        boundary.publish(event);
        verify(publisher).publishScholarshipEvent(event);
        evidence("valid-payload-result.json", serialized, "PASS", null, 1);
    }

    @Test
    void wrongAmountTypeFailsBeforePublisher() throws Exception {
        ScholarshipEvent event = realAppliedEvent();
        ObjectNode serialized = mapper.valueToTree(event);
        serialized.put("amount", "1500.00");
        AtomicInteger crossed = new AtomicInteger();
        ContractPayloadValidationException error = assertThrows(ContractPayloadValidationException.class,
                () -> boundary.publishSerialized(serialized, () -> {
                    crossed.incrementAndGet();
                    publisher.publishScholarshipEvent(event);
                }));
        assertTrue(error.getMessage().contains("amount"), error.getMessage());
        assertEquals(0, crossed.get());
        verifyNoInteractions(publisher);
        evidence("wrong-type-result.json", serialized, "FAIL", error.getMessage(), crossed.get());
    }

    @Test
    void missingStudentIdFailsBeforePublisher() throws Exception {
        ScholarshipEvent event = realAppliedEvent();
        ObjectNode serialized = mapper.valueToTree(event);
        serialized.remove("studentId");
        AtomicInteger crossed = new AtomicInteger();
        ContractPayloadValidationException error = assertThrows(ContractPayloadValidationException.class,
                () -> boundary.publishSerialized(serialized, () -> {
                    crossed.incrementAndGet();
                    publisher.publishScholarshipEvent(event);
                }));
        assertTrue(error.getMessage().contains("studentId"), error.getMessage());
        assertEquals(0, crossed.get());
        verifyNoInteractions(publisher);
        evidence("missing-required-result.json", serialized, "FAIL", error.getMessage(), crossed.get());
    }

    @Test
    void nullRequiredAmountIsRejected() {
        ScholarshipEvent event = realAppliedEvent();
        event.setAmount(null);
        ContractPayloadValidationException error = assertThrows(ContractPayloadValidationException.class,
                () -> boundary.publish(event));
        assertTrue(error.getMessage().contains("amount"), error.getMessage());
        verifyNoInteractions(publisher);
    }

    @Test
    void disabledStarterPropertyPreservesPublisherFlow() {
        properties.setEnabled(false);
        ScholarshipEvent event = realAppliedEvent();
        event.setAmount(null);
        boundary.publish(event);
        verify(publisher).publishScholarshipEvent(event);
    }

    @Test
    void realScholarshipServiceCreatesAndPublishesAppliedEventOnce() {
        ScholarshipService service = new ScholarshipService();
        ScholarshipRepository scholarships = mock(ScholarshipRepository.class);
        StudentRepository students = mock(StudentRepository.class);
        TaskProducer taskProducer = mock(TaskProducer.class);
        User user = new User();
        user.setUsername("demo-student");
        user.setEmail("demo@example.test");
        StudentProfile student = new StudentProfile();
        student.setId(7L);
        student.setUser(user);
        when(students.findById(7L)).thenReturn(Optional.of(student));
        when(scholarships.save(any(ScholarshipApplication.class))).thenAnswer(call -> {
            ScholarshipApplication saved = call.getArgument(0);
            saved.setId(101L);
            return saved;
        });
        ReflectionTestUtils.setField(service, "scholarshipRepository", scholarships);
        ReflectionTestUtils.setField(service, "studentRepository", students);
        ReflectionTestUtils.setField(service, "eventPublisher", publisher);
        ReflectionTestUtils.setField(service, "appliedEventBoundary", boundary);
        ReflectionTestUtils.setField(service, "taskProducer", taskProducer);
        ScholarshipDto request = new ScholarshipDto();
        request.setStudentId(7L);
        request.setScholarshipName("Access Grant");
        request.setAmountRequested(new BigDecimal("1500.00"));
        ScholarshipDto created = service.createScholarship(request);
        assertEquals(101L, created.getId());
        verify(publisher).publishScholarshipEvent(any(ScholarshipEvent.class));
        verify(taskProducer).sendEmailTask(any());
    }

    private void evidence(String name, JsonNode payload, String status, String error, int count) throws Exception {
        String directory = System.getenv("IEMS_DCG_RUNTIME_EVIDENCE");
        if (directory == null || directory.isBlank()) {
            return;
        }
        Path file = Path.of(directory).resolve(name);
        Files.createDirectories(file.getParent());
        byte[] payloadBytes = mapper.writeValueAsBytes(payload);
        byte[] schemaBytes = Files.readAllBytes(CONTRACTS.resolve("iems.scholarship.applied/v1.json"));
        Map<String, Object> row = Map.of(
                "contractId", ScholarshipAppliedEventBoundary.CONTRACT_ID,
                "version", ScholarshipAppliedEventBoundary.VERSION,
                "schemaSha256", sha(schemaBytes),
                "payloadSha256", sha(payloadBytes),
                "validation", status,
                "boundaryInvocationCount", count,
                "errorCategory", error == null ? "NONE" : "CONTRACT_PAYLOAD_INVALID",
                "message", error == null ? "" : error,
                "payload", payload);
        Files.writeString(file, mapper.writerWithDefaultPrettyPrinter().writeValueAsString(row) + "\n",
                StandardCharsets.UTF_8);
    }

    private String sha(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
}
