-- MetroPulse Database Schema
-- Migration 002: pgvector extension and case_studies table

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS case_studies (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  city        TEXT NOT NULL,
  year        INTEGER,
  description TEXT NOT NULL,
  tags        TEXT[],
  embedding   vector(1536),
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_studies_embedding
  ON case_studies
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
