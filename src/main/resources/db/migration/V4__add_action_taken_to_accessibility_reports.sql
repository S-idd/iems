-- Flyway migration V4: add action_taken column to accessibility_reports
-- This checks for existence and adds the column if missing (PostgreSQL-specific DO block)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'action_taken'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN action_taken TEXT;
    END IF;
END$$;
