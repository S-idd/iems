package com.iems.dcg;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

@Configuration
@Profile("db-demo")
@ConditionalOnProperty(prefix = "iems.dcg.webhook", name = "enabled", havingValue = "true")
public class DcgWebhookDemoConfig {
    @Bean
    DcgWebhookInbox dcgWebhookInbox(ObjectMapper mapper) {
        String path = System.getenv("IEMS_DCG_WEBHOOK_INBOX_DB");
        String authorization = System.getenv("IEMS_DCG_WEBHOOK_AUTH");
        if (path == null || path.isBlank() || authorization == null || authorization.isBlank()) {
            throw new IllegalStateException("IEMS_DCG_WEBHOOK_INBOX_DB and IEMS_DCG_WEBHOOK_AUTH are required when webhook demo is enabled");
        }
        return new DcgWebhookInbox(Path.of(path), authorization, mapper);
    }
}
