// JDBC schema snapshot / single-statement executor for the isolated gate demo.
// Driver + JSON classes come from the packaged DCG CLI JAR, not a DCG source build.
import java.sql.*;
import java.nio.file.*;
import java.util.*;
import com.fasterxml.jackson.databind.ObjectMapper;

class DatabaseTool {
    public static void main(String[] args) throws Exception {
        var props = new Properties();
        String user = System.getenv("IEMS_DB_USER");
        if (user != null && !user.isBlank()) {
            props.setProperty("user", user);
            props.setProperty("password", Objects.requireNonNullElse(System.getenv("IEMS_DB_PASSWORD"), ""));
        }
        try (var conn = DriverManager.getConnection(System.getenv("IEMS_JDBC_URL"), props)) {
            if (args[0].equals("execute")) {
                try (var statement = conn.createStatement()) { statement.execute(Files.readString(Path.of(args[1]))); }
                return;
            }
            if (args[0].equals("seed-notification")) {
                long adminId;
                try (var statement = conn.prepareStatement("SELECT id FROM users WHERE username = ?")) {
                    statement.setString(1, "demo-admin");
                    try (var rows = statement.executeQuery()) {
                        if (!rows.next()) throw new IllegalStateException("demo-admin is missing");
                        adminId = rows.getLong(1);
                        if (rows.next()) throw new IllegalStateException("demo-admin is not unique");
                    }
                }
                try (var statement = conn.prepareStatement(
                        "INSERT INTO notifications (user_id,title,message,type,is_read,created_at) " +
                        "VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)")) {
                    statement.setLong(1, adminId);
                    statement.setString(2, "Postman fixture");
                    statement.setString(3, "Notification endpoint check");
                    statement.setString(4, "TEST");
                    statement.setBoolean(5, false);
                    if (statement.executeUpdate() != 1) throw new IllegalStateException("Notification insert failed");
                }
                return;
            }
            if (args[0].equals("history")) {
                var checks = new ArrayList<Map<String, String>>();
                try (var statement = conn.prepareStatement(
                        "SELECT contract_id,status FROM check_runs ORDER BY created_at,run_id");
                     var rows = statement.executeQuery()) {
                    while (rows.next()) checks.add(Map.of(
                            "contractId", rows.getString(1), "status", rows.getString(2)));
                }
                new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(Path.of(args[1]).toFile(), checks);
                return;
            }
            if (!args[0].equals("snapshot") || !args[1].matches("[a-z][a-z0-9_]*"))
                throw new IllegalArgumentException("Expected snapshot TABLE FILE or execute SQL_FILE");
            var fields = new TreeMap<String, Object>();
            var required = new ArrayList<String>();
            String schema = conn.getMetaData().getDatabaseProductName().equals("PostgreSQL") ? conn.getSchema() : null;
            try (var rows = conn.getMetaData().getColumns(conn.getCatalog(), schema, args[1], "%")) {
                while (rows.next()) {
                    // JDBC table patterns treat underscores as wildcards; match the exact name too.
                    if (!rows.getString("TABLE_NAME").equals(args[1])) continue;
                    String name = rows.getString("COLUMN_NAME");
                    String type = switch(rows.getInt("DATA_TYPE")) {
                        case Types.INTEGER, Types.BIGINT, Types.SMALLINT, Types.TINYINT -> "integer";
                        case Types.DECIMAL, Types.NUMERIC, Types.FLOAT, Types.DOUBLE, Types.REAL -> "number";
                        case Types.BOOLEAN, Types.BIT -> "boolean";
                        default -> "string";
                    };
                    fields.put(name, Map.of("type", type));
                    if (rows.getInt("NULLABLE") == DatabaseMetaData.columnNoNulls) required.add(name);
                }
            }
            if (fields.isEmpty()) throw new IllegalStateException("No table columns found");
            Collections.sort(required);
            var result = Map.of("$schema", "https://json-schema.org/draft/2020-12/schema",
                                "type", "object", "properties", fields, "required", required);
            new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(Path.of(args[2]).toFile(), result);
        }
    }
}
