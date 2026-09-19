package com.iems.dcg.validation;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.kafka.support.JacksonUtils;

/** One JSON format for validation and the Kafka value serializer. */
public final class IemsEventJson {
    private IemsEventJson() {}

    public static ObjectMapper mapper() {
        return JacksonUtils.enhancedObjectMapper()
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    }
}
