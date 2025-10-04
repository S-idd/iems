-- Ensure classrooms table has required columns
DO $$
BEGIN
    -- If the table doesn't exist, create it with the expected schema
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'classrooms'
    ) THEN
        CREATE TABLE public.classrooms (
            id bigserial PRIMARY KEY,
            name varchar(100) NOT NULL,
            building varchar(50),
            room_number varchar(20),
            capacity integer,
            is_accessible boolean DEFAULT false,
            accessibility_features text,
            school_id bigint,
            created_at timestamp without time zone NOT NULL DEFAULT now(),
            updated_at timestamp without time zone
        );
        CREATE INDEX IF NOT EXISTS idx_classroom_school ON public.classrooms (school_id);
        CREATE INDEX IF NOT EXISTS idx_classroom_name ON public.classrooms (name);
    ELSE
        -- Table exists: add any missing columns
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'id'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN id bigserial;
            -- Try to set as primary key if possible
            BEGIN
                ALTER TABLE public.classrooms ADD PRIMARY KEY (id);
            EXCEPTION WHEN OTHERS THEN
                -- ignore if cannot add primary key
                NULL;
            END;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'name'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN name varchar(100) NOT NULL DEFAULT '';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'building'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN building varchar(50);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'room_number'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN room_number varchar(20);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'capacity'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN capacity integer;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'is_accessible'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN is_accessible boolean DEFAULT false;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'accessibility_features'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN accessibility_features text;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'school_id'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN school_id bigint;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN created_at timestamp without time zone NOT NULL DEFAULT now();
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'classrooms' AND column_name = 'updated_at'
        ) THEN
            ALTER TABLE public.classrooms ADD COLUMN updated_at timestamp without time zone;
        END IF;

        -- Ensure indexes exist
        CREATE INDEX IF NOT EXISTS idx_classroom_school ON public.classrooms (school_id);
        CREATE INDEX IF NOT EXISTS idx_classroom_name ON public.classrooms (name);
    END IF;
END$$;