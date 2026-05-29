-- MetroPulse Database Schema
-- Migration 006: near-real-time data ingestion and snapshot tables

CREATE TABLE IF NOT EXISTS data_sources (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                TEXT NOT NULL,
  domain              TEXT NOT NULL CHECK (domain IN ('mobility', 'jobs', 'land_value', 'census', 'news')),
  auth_type           TEXT NOT NULL DEFAULT 'none',
  update_cadence_sec  INTEGER NOT NULL,
  license_notes       TEXT,
  enabled             BOOLEAN NOT NULL DEFAULT false,
  created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_observations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id     UUID REFERENCES data_sources(id),
  city          TEXT NOT NULL,
  observed_at   TIMESTAMPTZ NOT NULL,
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload       JSONB NOT NULL,
  payload_hash  TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'ok',
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS h3_observations (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city              TEXT NOT NULL,
  h3_index          TEXT NOT NULL,
  metric            TEXT NOT NULL,
  value             DOUBLE PRECISION NOT NULL,
  observed_at       TIMESTAMPTZ NOT NULL,
  source_id         UUID REFERENCES data_sources(id),
  confidence        NUMERIC(4,3) NOT NULL DEFAULT 0.5,
  freshness_status  TEXT NOT NULL DEFAULT 'fresh',
  created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS city_snapshots (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city               TEXT NOT NULL,
  snapshot_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  h3_cells           JSONB NOT NULL,
  aggregate_metrics  JSONB NOT NULL,
  source_manifest    JSONB NOT NULL,
  quality_score      NUMERIC(4,3) NOT NULL DEFAULT 0,
  status             TEXT NOT NULL DEFAULT 'degraded',
  created_at         TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS news_events (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city         TEXT NOT NULL,
  topic        TEXT NOT NULL,
  title        TEXT NOT NULL,
  url          TEXT,
  published_at TIMESTAMPTZ,
  tone         DOUBLE PRECISION,
  impact_tags  TEXT[],
  source       TEXT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connector     TEXT NOT NULL,
  started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at  TIMESTAMPTZ,
  rows_read      INTEGER NOT NULL DEFAULT 0,
  rows_written   INTEGER NOT NULL DEFAULT 0,
  errors         JSONB NOT NULL DEFAULT '[]'::jsonb,
  status         TEXT NOT NULL DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS idx_raw_observations_city_time ON raw_observations(city, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_h3_observations_city_h3 ON h3_observations(city, h3_index);
CREATE INDEX IF NOT EXISTS idx_city_snapshots_city_time ON city_snapshots(city, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_events_city_time ON news_events(city, published_at DESC);
