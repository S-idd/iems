package com.iems.config;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ApprovedDemoMigrationsTest {
    @Test
    void rejectsAnAdditionalUnreviewedMigration() throws Exception {
        var approval = new ApprovedDemoMigrations();
        approval.verify("sqlite");
        Path extra = Path.of("target/test-classes/db/portable/sqlite/V999__unreviewed.sql");
        Files.createDirectories(extra.getParent());
        try {
            Files.writeString(extra, "alter table schools drop column name;\n");
            assertThrows(IllegalStateException.class, () -> approval.verify("sqlite"));
        } finally {
            Files.deleteIfExists(extra);
        }
    }
}
