-- Add foreign key constraints to accessibility_reports
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND constraint_name = 'fk_accessibility_school'
    ) THEN
        ALTER TABLE accessibility_reports
        ADD CONSTRAINT fk_accessibility_school FOREIGN KEY (school_id) REFERENCES school(id) ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND constraint_name = 'fk_accessibility_student'
    ) THEN
        ALTER TABLE accessibility_reports
        ADD CONSTRAINT fk_accessibility_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;