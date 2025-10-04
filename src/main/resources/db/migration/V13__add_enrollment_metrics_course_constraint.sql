-- Add foreign key constraint for course_id in enrollment_metrics
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND table_name = 'enrollment_metrics' AND constraint_name = 'fk_enrollment_course'
    ) THEN
        ALTER TABLE enrollment_metrics
        ADD CONSTRAINT fk_enrollment_course FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE;
    END IF;
END $$;