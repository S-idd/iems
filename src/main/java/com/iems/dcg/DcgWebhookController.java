package com.iems.dcg;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Explicit DCG demo inbox, separate from /api/notifications and disabled by default. */
@RestController
@Profile("db-demo")
@ConditionalOnProperty(prefix = "iems.dcg.webhook", name = "enabled", havingValue = "true")
@RequestMapping("/api/dcg")
public class DcgWebhookController {
    private final DcgWebhookInbox inbox;

    public DcgWebhookController(DcgWebhookInbox inbox) {
        this.inbox = inbox;
    }

    @PostMapping("/webhook")
    public ResponseEntity<Map<String, Object>> receive(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestBody JsonNode event) {
        inbox.requireAuthorization(authorization);
        Map<String, Object> accepted = inbox.accept(event);
        return ResponseEntity.status(Boolean.TRUE.equals(accepted.get("duplicate")) ? 200 : 202).body(accepted);
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, String>> handleDemoRequestError(ResponseStatusException error) {
        return ResponseEntity.status(error.getStatusCode()).body(Map.of("error", error.getReason()));
    }

    @GetMapping("/events")
    public List<Map<String, Object>> events(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestParam(value = "runId", required = false) String runId,
            @RequestParam(value = "eventType", required = false) String eventType) {
        inbox.requireAuthorization(authorization);
        return inbox.list(runId, eventType);
    }
}
