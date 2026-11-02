CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS dataset_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_key TEXT NOT NULL,
  version TEXT NOT NULL,
  checksum TEXT NOT NULL,
  transform_version TEXT NOT NULL,
  observed_at TIMESTAMPTZ,
  manifest JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source_key, version, checksum)
);
