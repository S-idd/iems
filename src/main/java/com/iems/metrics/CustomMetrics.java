package com.iems.metrics;

import java.util.concurrent.TimeUnit;

import org.springframework.stereotype.Component;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;

/**
 * Custom business metrics for IEMS application.
 */
@Component
public class CustomMetrics {

    private final MeterRegistry meterRegistry;
    
    // Counters
    private final Counter scholarshipApplicationsCounter;
    private final Counter scholarshipApprovalsCounter;
    private final Counter scholarshipRejectionsCounter;
    private final Counter accessibilityReportsCounter;
    private final Counter accessibilityReportsResolvedCounter;
    private final Counter enrollmentsCounter;
    
    // Timers
    private final Timer scholarshipProcessingTimer;
    private final Timer accessibilityResolutionTimer;

    public CustomMetrics(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
        
        // Initialize counters
        this.scholarshipApplicationsCounter = Counter.builder("iems.scholarships.applications.total")
                .description("Total number of scholarship applications submitted")
                .register(meterRegistry);
                
        this.scholarshipApprovalsCounter = Counter.builder("iems.scholarships.approvals.total")
                .description("Total number of scholarship applications approved")
                .register(meterRegistry);
                
        this.scholarshipRejectionsCounter = Counter.builder("iems.scholarships.rejections.total")
                .description("Total number of scholarship applications rejected")
                .register(meterRegistry);
                
        this.accessibilityReportsCounter = Counter.builder("iems.accessibility.reports.total")
                .description("Total number of accessibility reports created")
                .register(meterRegistry);
                
        this.accessibilityReportsResolvedCounter = Counter.builder("iems.accessibility.reports.resolved.total")
                .description("Total number of accessibility reports resolved")
                .register(meterRegistry);
                
        this.enrollmentsCounter = Counter.builder("iems.enrollments.total")
                .description("Total number of course enrollments")
                .register(meterRegistry);
        
        // Initialize timers
        this.scholarshipProcessingTimer = Timer.builder("iems.scholarships.processing.time")
                .description("Time taken to process scholarship applications")
                .register(meterRegistry);
                
        this.accessibilityResolutionTimer = Timer.builder("iems.accessibility.resolution.time")
                .description("Time taken to resolve accessibility reports")
                .register(meterRegistry);
    }

    // Scholarship metrics
    public void incrementScholarshipApplications() {
        scholarshipApplicationsCounter.increment();
    }

    public void incrementScholarshipApprovals() {
        scholarshipApprovalsCounter.increment();
    }

    public void incrementScholarshipRejections() {
        scholarshipRejectionsCounter.increment();
    }

    public void recordScholarshipProcessingTime(long milliseconds) {
        scholarshipProcessingTimer.record(milliseconds, TimeUnit.MILLISECONDS);
    }

    // Accessibility metrics
    public void incrementAccessibilityReports() {
        accessibilityReportsCounter.increment();
    }

    public void incrementAccessibilityReportsResolved() {
        accessibilityReportsResolvedCounter.increment();
    }

    public void recordAccessibilityResolutionTime(long milliseconds) {
        accessibilityResolutionTimer.record(milliseconds, TimeUnit.MILLISECONDS);
    }

    // Enrollment metrics
    public void incrementEnrollments() {
        enrollmentsCounter.increment();
    }

    // Gauge for real-time metrics
    public void registerGauge(String name, String description, Number number) {
        meterRegistry.gauge(name, number);
    }

    // Tag-based metrics
    public void incrementCounterWithTags(String name, String... tags) {
        Counter.builder(name)
                .tags(tags)
                .register(meterRegistry)
                .increment();
    }
}