-- Add action_taken column to accessibility_reports
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'action_taken'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN action_taken TEXT;
    END IF;
END$$;