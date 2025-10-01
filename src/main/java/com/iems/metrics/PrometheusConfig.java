package com.iems.metrics;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Configuration for Prometheus metrics.
 */
@Configuration
public class PrometheusConfig {

    @Autowired
    private MeterRegistry meterRegistry;

    @Bean
    public CustomMetrics customMetrics() {
        return new CustomMetrics(meterRegistry);
    }
}