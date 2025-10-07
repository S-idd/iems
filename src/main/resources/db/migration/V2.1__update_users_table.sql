-- V2.1: Additional updates to users table and school table enhancements
-- This migration adds any missing columns or constraints that weren't in V2

DO $$
BEGIN
    -- Add profile_picture column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'profile_picture'
    ) THEN
        ALTER TABLE users ADD COLUMN profile_picture VARCHAR(500);
    END IF;

    -- Add bio/description column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'bio'
    ) THEN
        ALTER TABLE users ADD COLUMN bio TEXT;
    END IF;

    -- Add date_of_birth column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'date_of_birth'
    ) THEN
        ALTER TABLE users ADD COLUMN date_of_birth DATE;
    END IF;

    -- Add address column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'address'
    ) THEN
        ALTER TABLE users ADD COLUMN address VARCHAR(500);
    END IF;

    -- Add city column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'city'
    ) THEN
        ALTER TABLE users ADD COLUMN city VARCHAR(100);
    END IF;

    -- Add state column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'state'
    ) THEN
        ALTER TABLE users ADD COLUMN state VARCHAR(100);
    END IF;

    -- Add postal_code column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'postal_code'
    ) THEN
        ALTER TABLE users ADD COLUMN postal_code VARCHAR(20);
    END IF;

    -- Add country column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'country'
    ) THEN
        ALTER TABLE users ADD COLUMN country VARCHAR(100) DEFAULT 'India';
    END IF;
END$$;

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);

-- Create index on school_id for faster joins
CREATE INDEX IF NOT EXISTS idx_user_schools_id ON users(schools_id);

-- Create index on active status
CREATE INDEX IF NOT EXISTS idx_user_active ON users(active);

-- Add trigger to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_user_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_updated_at_column();

-- Add comments to columns for documentation
COMMENT ON COLUMN users.role IS 'User role: ADMIN, TEACHER, STUDENT, STAFF';
COMMENT ON COLUMN users.email_verified IS 'Whether user has verified their email address';
COMMENT ON COLUMN users.refresh_token IS 'JWT refresh token for authentication';
COMMENT ON COLUMN users.schools_id IS 'Reference to schools table';