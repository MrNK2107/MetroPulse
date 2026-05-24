-- MetroPulse Database Schema
-- Migration 003: Extend case_studies table with additional fields

ALTER TABLE case_studies ADD COLUMN IF NOT EXISTS outcome TEXT;
ALTER TABLE case_studies ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE case_studies ADD COLUMN IF NOT EXISTS sectors TEXT[];
ALTER TABLE case_studies ADD COLUMN IF NOT EXISTS policies TEXT[];
ALTER TABLE case_studies ADD COLUMN IF NOT EXISTS embedding_model TEXT DEFAULT 'text-embedding-3-small';
