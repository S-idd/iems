package com.iems.dcg;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.server.ResponseStatusException;

class DcgWebhookInboxTest {
    @TempDir Path temp;
    private final ObjectMapper mapper = new ObjectMapper();

    private JsonNode event(String eventId, String runId) throws Exception {
        return mapper.readTree("""
                {"eventId":"%s","eventType":"CONTRACT_CHECK_FAILED","contractId":"iems.enrollment",
                 "runId":"%s","dedupeKey":"CONTRACT_CHECK_FAILED:iems.enrollment:%s",
                 "breakingChanges":["Field type changed: studentId (integer -> string)"]}
                """.formatted(eventId, runId, runId));
    }

    @Test
    void requiresSecretBeforePersisting() throws Exception {
        DcgWebhookInbox inbox = new DcgWebhookInbox(temp.resolve("inbox.db"), "Bearer demo-secret", mapper);
        ResponseStatusException missing = assertThrows(ResponseStatusException.class,
                () -> inbox.requireAuthorization(null));
        assertEquals(HttpStatus.UNAUTHORIZED, missing.getStatusCode());
        assertThrows(ResponseStatusException.class, () -> inbox.requireAuthorization("Bearer wrong"));
        assertTrue(inbox.list(null, null).isEmpty());
    }

    @Test
    void persistsCorrelatedEventAcrossReopenAndDeduplicatesRetry() throws Exception {
        Path database = temp.resolve("inbox.db");
        DcgWebhookInbox inbox = new DcgWebhookInbox(database, "Bearer demo-secret", mapper);
        JsonNode event = event("event-1", "run-1");
        inbox.requireAuthorization("Bearer demo-secret");
        assertFalse((Boolean) inbox.accept(event).get("duplicate"));
        assertTrue((Boolean) inbox.accept(event).get("duplicate"));
        DcgWebhookInbox reopened = new DcgWebhookInbox(database, "Bearer demo-secret", mapper);
        var rows = reopened.list("run-1", "CONTRACT_CHECK_FAILED");
        assertEquals(1, rows.size());
        assertEquals("event-1", rows.get(0).get("eventId"));
        assertEquals("run-1", rows.get(0).get("runId"));
        assertEquals("iems.enrollment", rows.get(0).get("contractId"));
        assertTrue(reopened.list("other-run", null).isEmpty());
    }

    @Test
    void controllerReturnsAuthAndValidationStatuses() throws Exception {
        DcgWebhookInbox inbox = new DcgWebhookInbox(temp.resolve("inbox.db"), "Basic demo-secret", mapper);
        var mvc = MockMvcBuilders.standaloneSetup(new DcgWebhookController(inbox)).build();
        mvc.perform(get("/api/dcg/events")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/dcg/webhook").contentType(MediaType.APPLICATION_JSON)
                .content(event("event-1", "run-1").toString())).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/dcg/webhook").header("Authorization", "Basic demo-secret")
                .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/dcg/webhook").header("Authorization", "Basic demo-secret")
                .contentType(MediaType.APPLICATION_JSON).content(event("event-1", "run-1").toString()))
                .andExpect(status().isAccepted());
        mvc.perform(post("/api/dcg/webhook").header("Authorization", "Basic demo-secret")
                .contentType(MediaType.APPLICATION_JSON).content(event("event-1", "run-1").toString()))
                .andExpect(status().isOk());
    }

    @Test
    void rejectsMalformedOrConflictingEvent() throws Exception {
        DcgWebhookInbox inbox = new DcgWebhookInbox(temp.resolve("inbox.db"), "Bearer demo-secret", mapper);
        assertEquals(HttpStatus.BAD_REQUEST, assertThrows(ResponseStatusException.class,
                () -> inbox.accept(mapper.readTree("{}"))).getStatusCode());
        inbox.accept(event("event-1", "run-1"));
        assertEquals(HttpStatus.CONFLICT, assertThrows(ResponseStatusException.class,
                () -> inbox.accept(event("event-1", "run-2"))).getStatusCode());
    }
}
