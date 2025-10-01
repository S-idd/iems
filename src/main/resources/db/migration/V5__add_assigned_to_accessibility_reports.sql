-- Flyway migration V5: add assigned_to (and ensure reported_by) columns to accessibility_reports
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'assigned_to'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN assigned_to bigint;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'reported_by'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN reported_by bigint;
    END IF;
END$$;
