package com.iems.dcg;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermission;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

/** Demo-only, independent DCG event inbox. Never writes to IEMS user notifications. */
public final class DcgWebhookInbox {
    private final Path database;
    private final byte[] expectedAuthorization;
    private final ObjectMapper mapper;

    public DcgWebhookInbox(Path database, String authorization, ObjectMapper mapper) {
        if (database == null || !database.isAbsolute() || authorization == null || authorization.isBlank()) {
            throw new IllegalArgumentException("Absolute inbox path and nonempty webhook authorization are required");
        }
        this.database = database.normalize();
        this.expectedAuthorization = authorization.getBytes(StandardCharsets.UTF_8);
        this.mapper = mapper;
        initialize();
    }

    public void requireAuthorization(String supplied) {
        byte[] received = supplied == null ? new byte[0] : supplied.getBytes(StandardCharsets.UTF_8);
        if (!MessageDigest.isEqual(expectedAuthorization, received)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "DCG webhook authorization required");
        }
    }

    public synchronized Map<String, Object> accept(JsonNode event) {
        if (event == null || !event.isObject()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "DCG event must be an object");
        }
        String eventId = required(event, "eventId");
        String type = required(event, "eventType");
        String contractId = required(event, "contractId");
        String dedupeKey = required(event, "dedupeKey");
        String runId = optional(event, "runId");
        if ("CONTRACT_CHECK_FAILED".equals(type) && runId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Failed check event requires runId");
        }
        if (eventId.length() > 100 || type.length() > 100 || contractId.length() > 200 || dedupeKey.length() > 500
                || (runId != null && runId.length() > 100)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "DCG event field too long");
        }
        try (Connection connection = connect();
             PreparedStatement insert = connection.prepareStatement("""
                 INSERT OR IGNORE INTO dcg_events
                 (event_id, dedupe_key, event_type, contract_id, run_id, received_at, payload_json)
                 VALUES (?, ?, ?, ?, ?, ?, ?)
                 """)) {
            insert.setString(1, eventId);
            insert.setString(2, dedupeKey);
            insert.setString(3, type);
            insert.setString(4, contractId);
            insert.setString(5, runId);
            insert.setString(6, Instant.now().toString());
            insert.setString(7, mapper.writeValueAsString(event));
            boolean created = insert.executeUpdate() == 1;
            if (!created && !sameEvent(eventId, dedupeKey)) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "DCG event identity conflict");
            }
            return Map.of("eventId", eventId, "accepted", true, "duplicate", !created);
        } catch (SQLException | IOException error) {
            throw new IllegalStateException("DCG inbox could not persist event", error);
        }
    }

    public synchronized List<Map<String, Object>> list(String runId, String eventType) {
        String sql = "SELECT event_id, event_type, contract_id, run_id, dedupe_key, received_at, payload_json "
                + "FROM dcg_events WHERE (? IS NULL OR run_id = ?) AND (? IS NULL OR event_type = ?) "
                + "ORDER BY received_at, event_id LIMIT 100";
        try (Connection connection = connect(); PreparedStatement query = connection.prepareStatement(sql)) {
            query.setString(1, runId);
            query.setString(2, runId);
            query.setString(3, eventType);
            query.setString(4, eventType);
            List<Map<String, Object>> rows = new ArrayList<>();
            try (ResultSet result = query.executeQuery()) {
                while (result.next()) {
                    rows.add(Map.of("eventId", result.getString(1), "eventType", result.getString(2),
                            "contractId", result.getString(3), "runId", result.getString(4) == null ? "" : result.getString(4),
                            "dedupeKey", result.getString(5), "receivedAt", result.getString(6),
                            "payload", mapper.readTree(result.getString(7))));
                }
            }
            return rows;
        } catch (SQLException | IOException error) {
            throw new IllegalStateException("DCG inbox could not read events", error);
        }
    }

    public Path database() {
        return database;
    }

    private boolean sameEvent(String eventId, String dedupeKey) throws SQLException {
        try (Connection connection = connect(); PreparedStatement query = connection.prepareStatement(
                "SELECT dedupe_key FROM dcg_events WHERE event_id = ?")) {
            query.setString(1, eventId);
            try (ResultSet result = query.executeQuery()) {
                return result.next() && dedupeKey.equals(result.getString(1));
            }
        }
    }

    private void initialize() {
        try {
            boolean parentExisted = Files.exists(database.getParent());
            Files.createDirectories(database.getParent());
            if (!parentExisted) {
                privatePermissions(database.getParent(), true);
            }
            try (Connection connection = connect(); Statement statement = connection.createStatement()) {
                statement.execute("""
                    CREATE TABLE IF NOT EXISTS dcg_events (
                      event_id TEXT PRIMARY KEY,
                      dedupe_key TEXT NOT NULL UNIQUE,
                      event_type TEXT NOT NULL,
                      contract_id TEXT NOT NULL,
                      run_id TEXT,
                      received_at TEXT NOT NULL,
                      payload_json TEXT NOT NULL
                    )
                    """);
                statement.execute("CREATE INDEX IF NOT EXISTS idx_dcg_events_run ON dcg_events(run_id)");
            }
            privatePermissions(database, false);
        } catch (IOException | SQLException error) {
            throw new IllegalStateException("DCG inbox initialization failed", error);
        }
    }

    private Connection connect() throws SQLException {
        Connection connection = DriverManager.getConnection("jdbc:sqlite:" + database);
        try (Statement statement = connection.createStatement()) {
            statement.execute("PRAGMA busy_timeout=5000");
        }
        return connection;
    }

    private void privatePermissions(Path path, boolean directory) throws IOException {
        try {
            Files.setPosixFilePermissions(path, directory
                    ? EnumSet.of(PosixFilePermission.OWNER_READ, PosixFilePermission.OWNER_WRITE, PosixFilePermission.OWNER_EXECUTE)
                    : EnumSet.of(PosixFilePermission.OWNER_READ, PosixFilePermission.OWNER_WRITE));
        } catch (UnsupportedOperationException ignored) {
            // The rehearsal runner also sets umask 077 on filesystems without POSIX permissions.
        }
    }

    private static String required(JsonNode event, String name) {
        String value = optional(event, name);
        if (value == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "DCG event requires " + name);
        }
        return value;
    }

    private static String optional(JsonNode event, String name) {
        JsonNode field = event.path(name);
        if (!field.isTextual()) {
            return null;
        }
        String value = field.asText().trim();
        return value.isEmpty() ? null : value;
    }
}
