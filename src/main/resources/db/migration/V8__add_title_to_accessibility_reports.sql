-- Flyway migration V8: add title column to accessibility_reports
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'title'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN title varchar(200) NOT NULL DEFAULT '';
    END IF;
END$$;
