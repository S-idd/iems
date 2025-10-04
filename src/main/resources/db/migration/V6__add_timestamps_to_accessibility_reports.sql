-- Add created_at and updated_at columns to accessibility_reports
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN created_at timestamp without time zone NOT NULL DEFAULT now();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN updated_at timestamp without time zone;
    END IF;
END$$;