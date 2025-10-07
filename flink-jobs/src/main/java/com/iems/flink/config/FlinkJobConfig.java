package com.iems.flink.config;

import java.io.Serializable;

/**
 * Configuration for Flink streaming jobs.
 */
public class FlinkJobConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    private String kafkaBootstrapServers;
    private String kafkaGroupId;
    private String dbHost;
    private String dbPort;
    private String dbName;
    private String dbUsername;
    private String dbPassword;

    public FlinkJobConfig() {
        // Load from environment variables
        this.kafkaBootstrapServers = System.getenv().getOrDefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092");
        this.kafkaGroupId = System.getenv().getOrDefault("KAFKA_GROUP_ID", "flink-accessibility-metrics");
        this.dbHost = System.getenv().getOrDefault("DB_HOST", "localhost");
        this.dbPort = System.getenv().getOrDefault("DB_PORT", "5432");
        this.dbName = System.getenv().getOrDefault("DB_NAME", "iemsdb");
        this.dbUsername = System.getenv().getOrDefault("DB_USERNAME", "iemsuser");
        this.dbPassword = System.getenv().getOrDefault("DB_PASSWORD", "iemspass");
    }

    public String getKafkaBootstrapServers() {
        return kafkaBootstrapServers;
    }

    public void setKafkaBootstrapServers(String kafkaBootstrapServers) {
        this.kafkaBootstrapServers = kafkaBootstrapServers;
    }

    public String getKafkaGroupId() {
        return kafkaGroupId;
    }

    public void setKafkaGroupId(String kafkaGroupId) {
        this.kafkaGroupId = kafkaGroupId;
    }

    public String getDbHost() {
        return dbHost;
    }

    public void setDbHost(String dbHost) {
        this.dbHost = dbHost;
    }

    public String getDbPort() {
        return dbPort;
    }

    public void setDbPort(String dbPort) {
        this.dbPort = dbPort;
    }

    public String getDbName() {
        return dbName;
    }

    public void setDbName(String dbName) {
        this.dbName = dbName;
    }

    public String getDbUsername() {
        return dbUsername;
    }

    public void setDbUsername(String dbUsername) {
        this.dbUsername = dbUsername;
    }

    public String getDbPassword() {
        return dbPassword;
    }

    public void setDbPassword(String dbPassword) {
        this.dbPassword = dbPassword;
    }

    public String getJdbcUrl() {
        return String.format("jdbc:postgresql://%s:%s/%s", dbHost, dbPort, dbName);
    }
}