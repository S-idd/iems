package com.iems.config;

import java.io.InputStream;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import org.flywaydb.core.Flyway;
import org.springframework.boot.autoconfigure.flyway.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;

/** Fail closed before Flyway when a portable demo migration has changed or appeared. */
@Configuration
@Profile("db-demo")
public class ApprovedDemoMigrations {
    @Bean
    FlywayMigrationStrategy approvedDemoMigrationStrategy() {
        return flyway -> {
            String vendor = vendor(flyway);
            verify(vendor);
            flyway.migrate();
        };
    }

    private String vendor(Flyway flyway) {
        var locations = flyway.getConfiguration().getLocations();
        if (locations.length != 1) throw new IllegalStateException("Expected one approved migration location");
        String path = locations[0].getDescriptor();
        for (String vendor : new String[]{"postgres", "mysql", "sqlite"}) {
            if (path.equals("classpath:db/portable/" + vendor)) return vendor;
        }
        throw new IllegalStateException("Unapproved migration location: " + path);
    }

    void verify(String vendor) {
        try {
            var loader = getClass().getClassLoader();
            var properties = new Properties();
            try (InputStream stream = loader.getResourceAsStream("db/portable/approved.sha256")) {
                if (stream == null) throw new IllegalStateException("Migration approval manifest missing");
                properties.load(stream);
            }
            Map<String, String> expected = new HashMap<>();
            for (String name : properties.stringPropertyNames()) {
                if (name.startsWith(vendor + "/")) expected.put(name.substring(vendor.length() + 1), properties.getProperty(name));
            }
            if (expected.isEmpty()) throw new IllegalStateException("No approved migrations for " + vendor);
            var resolver = new PathMatchingResourcePatternResolver(loader);
            var files = resolver.getResources("classpath*:db/portable/" + vendor + "/V*.sql");
            if (files.length != expected.size()) throw new IllegalStateException("Unapproved migration count for " + vendor);
            for (var file : files) {
                String filename = file.getFilename();
                byte[] contents;
                try (var stream = file.getInputStream()) { contents = stream.readAllBytes(); }
                String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(contents));
                if (!hash.equals(expected.remove(filename))) {
                    throw new IllegalStateException("Unapproved migration: " + vendor + "/" + filename);
                }
            }
            if (!expected.isEmpty()) throw new IllegalStateException("Approved migration missing for " + vendor);
        } catch (IllegalStateException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new IllegalStateException("Could not verify approved demo migrations", exception);
        }
    }
}
