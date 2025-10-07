-- Create tables for Flink aggregated metrics and analytics

-- First, ensure schools table exists (in case V2 didn't run properly)
CREATE TABLE IF NOT EXISTS schools (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    city VARCHAR(100),
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Accessibility metrics weekly aggregation
CREATE TABLE IF NOT EXISTS accessibility_metrics_weekly (
    id BIGSERIAL PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    report_count BIGINT NOT NULL DEFAULT 0,
    resolved_count BIGINT DEFAULT 0,
    high_severity_count BIGINT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(school_id, week_start_date)
);

CREATE INDEX IF NOT EXISTS idx_accessibility_metrics_school ON accessibility_metrics_weekly(school_id);
CREATE INDEX IF NOT EXISTS idx_accessibility_metrics_week ON accessibility_metrics_weekly(week_start_date);

-- Scholarship metrics aggregation
CREATE TABLE IF NOT EXISTS scholarship_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    total_applications BIGINT DEFAULT 0,
    approved_applications BIGINT DEFAULT 0,
    rejected_applications BIGINT DEFAULT 0,
    pending_applications BIGINT DEFAULT 0,
    total_amount_requested DECIMAL(12,2) DEFAULT 0,
    total_amount_approved DECIMAL(12,2) DEFAULT 0,
    average_processing_days DECIMAL(5,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_date)
);

CREATE INDEX IF NOT EXISTS idx_scholarship_metrics_date ON scholarship_metrics(metric_date);

-- Enrollment metrics
CREATE TABLE IF NOT EXISTS enrollment_metrics (
    id BIGSERIAL PRIMARY KEY,
    school_id BIGINT REFERENCES schools(id) ON DELETE CASCADE,
    course_id BIGINT, -- Will reference courses(id) after V11
    semester VARCHAR(100),
    academic_year VARCHAR(20),
    total_enrolled BIGINT DEFAULT 0,
    active_enrolled BIGINT DEFAULT 0,
    completed BIGINT DEFAULT 0,
    dropped BIGINT DEFAULT 0,
    average_grade DECIMAL(5,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_enrollment_metrics_school ON enrollment_metrics(school_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_metrics_course ON enrollment_metrics(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_metrics_semester ON enrollment_metrics(semester, academic_year);

-- Student demographics and diversity metrics
CREATE TABLE IF NOT EXISTS student_diversity_metrics (
    id BIGSERIAL PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    total_students BIGINT DEFAULT 0,
    students_with_disabilities BIGINT DEFAULT 0,
    visual_impairment_count BIGINT DEFAULT 0,
    hearing_impairment_count BIGINT DEFAULT 0,
    physical_impairment_count BIGINT DEFAULT 0,
    cognitive_impairment_count BIGINT DEFAULT 0,
    multiple_disabilities_count BIGINT DEFAULT 0,
    accommodations_provided BIGINT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(school_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_diversity_metrics_school ON student_diversity_metrics(school_id);
CREATE INDEX IF NOT EXISTS idx_diversity_metrics_date ON student_diversity_metrics(metric_date);

-- System audit log for tracking changes
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id BIGINT NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);

-- Real-time dashboard metrics cache
CREATE TABLE IF NOT EXISTS dashboard_metrics_cache (
    id BIGSERIAL PRIMARY KEY,
    school_id BIGINT REFERENCES schools(id) ON DELETE CASCADE,
    metric_key VARCHAR(100) NOT NULL,
    metric_value TEXT NOT NULL,
    metric_type VARCHAR(50),
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(school_id, metric_key)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_cache_school ON dashboard_metrics_cache(school_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_cache_key ON dashboard_metrics_cache(metric_key);
CREATE INDEX IF NOT EXISTS idx_dashboard_cache_expires ON dashboard_metrics_cache(expires_at);

-- Event processing watermarks for Flink
CREATE TABLE IF NOT EXISTS event_watermarks (
    id BIGSERIAL PRIMARY KEY,
    topic_name VARCHAR(255) NOT NULL UNIQUE,
    last_processed_timestamp TIMESTAMP NOT NULL,
    last_processed_offset BIGINT,
    partition_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watermarks_topic ON event_watermarks(topic_name);

-- Function to update timestamp on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to update updated_at automatically
DROP TRIGGER IF EXISTS update_accessibility_metrics_weekly_updated_at ON accessibility_metrics_weekly;
CREATE TRIGGER update_accessibility_metrics_weekly_updated_at
    BEFORE UPDATE ON accessibility_metrics_weekly
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_scholarship_metrics_updated_at ON scholarship_metrics;
CREATE TRIGGER update_scholarship_metrics_updated_at
    BEFORE UPDATE ON scholarship_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_enrollment_metrics_updated_at ON enrollment_metrics;
CREATE TRIGGER update_enrollment_metrics_updated_at
    BEFORE UPDATE ON enrollment_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();