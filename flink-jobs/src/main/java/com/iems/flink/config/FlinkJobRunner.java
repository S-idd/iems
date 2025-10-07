package com.iems.flink.config;

import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class FlinkJobRunner implements CommandLineRunner {

    @Override
    public void run(String... args) throws Exception {
        // Execute the Flink job with the provided arguments
        com.iems.flink.AccessibilityMetricsJob.main(args);
    }
}