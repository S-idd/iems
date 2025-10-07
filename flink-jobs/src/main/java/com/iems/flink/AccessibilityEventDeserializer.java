package com.iems.flink;

import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;

public class AccessibilityEventDeserializer implements DeserializationSchema<AccessibilityEventRecord> {
    private static final long serialVersionUID = 1L;
    private static final Logger LOG = LoggerFactory.getLogger(AccessibilityEventDeserializer.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Override
    public AccessibilityEventRecord deserialize(byte[] message) throws IOException {
        try {
            return MAPPER.readValue(message, AccessibilityEventRecord.class);
        } catch (Exception e) {
            LOG.error("Failed to deserialize Kafka message: {}", new String(message), e);
            throw new IOException("Deserialization failed", e);
        }
    }

    @Override
    public boolean isEndOfStream(AccessibilityEventRecord nextElement) {
        return false;
    }

    @Override
    public TypeInformation<AccessibilityEventRecord> getProducedType() {
        return TypeInformation.of(AccessibilityEventRecord.class);
    }
}