-- V3: metrics tables
CREATE TABLE IF NOT EXISTS metrics (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(255),
  value DOUBLE PRECISION
);
