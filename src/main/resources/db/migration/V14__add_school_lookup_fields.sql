-- Optional fields preserve existing schools and existing create requests.
ALTER TABLE schools ADD COLUMN code VARCHAR(50);
ALTER TABLE schools ADD COLUMN district VARCHAR(100);
-- Match the case-insensitive API lookup, including concurrent inserts.
CREATE UNIQUE INDEX uq_schools_code_ignore_case ON schools (LOWER(code));
