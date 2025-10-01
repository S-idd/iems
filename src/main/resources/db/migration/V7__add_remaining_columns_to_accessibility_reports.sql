-- Flyway migration V7: add remaining columns expected by AccessibilityReport entity
DO $$
BEGIN
    -- description
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'description'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN description TEXT;
    END IF;

    -- related_disability
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'related_disability'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN related_disability varchar(50);
    END IF;

    -- report_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'report_date'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN report_date date NOT NULL DEFAULT CURRENT_DATE;
    END IF;

    -- incident_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'incident_date'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN incident_date date;
    END IF;

    -- location
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'location'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN location varchar(200);
    END IF;

    -- severity
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'severity'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN severity varchar(50);
    END IF;

    -- follow_up_required
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'follow_up_required'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN follow_up_required boolean DEFAULT false;
    END IF;

    -- follow_up_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'follow_up_date'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN follow_up_date date;
    END IF;

    -- resolved
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'resolved'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN resolved boolean DEFAULT false;
    END IF;

    -- resolved_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'resolved_date'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN resolved_date date;
    END IF;

    -- student_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'student_id'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN student_id bigint;
    END IF;

    -- school_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'accessibility_reports' AND column_name = 'school_id'
    ) THEN
        ALTER TABLE public.accessibility_reports ADD COLUMN school_id bigint;
    END IF;
END$$;
