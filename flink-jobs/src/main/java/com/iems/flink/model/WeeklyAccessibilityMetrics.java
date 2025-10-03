package com.iems.flink.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDate;
import java.util.Map;

/**
 * Represents weekly accessibility metrics aggregated by school.
 */
public class WeeklyAccessibilityMetrics {

    @JsonProperty("schoolId")
    private Long schoolId;

    @JsonProperty("weekStart")
    private LocalDate weekStart;

    @JsonProperty("weekEnd")
    private LocalDate weekEnd;

    @JsonProperty("totalReports")
    private Long totalReports;

    @JsonProperty("avgSeverity")
    private Double avgSeverity;

    @JsonProperty("reportsByDisability")
    private Map<String, Long> reportsByDisability;

    // Getters and Setters
    public Long getSchoolId() { return schoolId; }
    public void setSchoolId(Long schoolId) { this.schoolId = schoolId; }

    public LocalDate getWeekStart() { return weekStart; }
    public void setWeekStart(LocalDate weekStart) { this.weekStart = weekStart; }

    public LocalDate getWeekEnd() { return weekEnd; }
    public void setWeekEnd(LocalDate weekEnd) { this.weekEnd = weekEnd; }

    public Long getTotalReports() { return totalReports; }
    public void setTotalReports(Long totalReports) { this.totalReports = totalReports; }

    public Double getAvgSeverity() { return avgSeverity; }
    public void setAvgSeverity(Double avgSeverity) { this.avgSeverity = avgSeverity; }

    public Map<String, Long> getReportsByDisability() { return reportsByDisability; }
    public void setReportsByDisability(Map<String, Long> reportsByDisability) { this.reportsByDisability = reportsByDisability; }

    @Override
    public String toString() {
        return "WeeklyAccessibilityMetrics{" +
                "schoolId=" + schoolId +
                ", weekStart=" + weekStart +
                ", weekEnd=" + weekEnd +
                ", totalReports=" + totalReports +
                ", avgSeverity=" + avgSeverity +
                ", reportsByDisability=" + reportsByDisability +
                '}';
    }
}