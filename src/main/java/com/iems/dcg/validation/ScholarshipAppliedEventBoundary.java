package com.iems.dcg.validation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ideas.contracts.starter.ContractPayloadValidator;
import com.ideas.contracts.starter.ContractValidationProperties;
import com.iems.kafka.model.ScholarshipEvent;
import com.iems.service.EventPublisherService;
import org.springframework.stereotype.Component;

/** Validates the real APPLIED event immediately before the existing IEMS publisher. */
@Component
public class ScholarshipAppliedEventBoundary {
    public static final String CONTRACT_ID = "iems.scholarship.applied";
    public static final String VERSION = "v1";

    private final ContractPayloadValidator validator;
    private final ContractValidationProperties properties;
    private final ObjectMapper mapper;
    private final EventPublisherService publisher;

    public ScholarshipAppliedEventBoundary(ContractPayloadValidator validator,
                                            ContractValidationProperties properties,
                                            EventPublisherService publisher) {
        this.validator = validator;
        this.properties = properties;
        this.mapper = IemsEventJson.mapper();
        this.publisher = publisher;
    }

    public void publish(ScholarshipEvent event) {
        JsonNode serialized = mapper.valueToTree(event);
        publishSerialized(serialized, () -> publisher.publishScholarshipEvent(event));
    }

    // The same serialized boundary is exercised with malformed JSON in tests. A typed
    // ScholarshipEvent cannot hold a string in its BigDecimal amount field.
    void publishSerialized(JsonNode serialized, Runnable publishAction) {
        if (properties.isEnabled()) {
            validator.validate(CONTRACT_ID, VERSION, serialized);
        }
        publishAction.run();
    }
}
