-- MetroPulse Database Schema
-- Migration 001: Core tables

-- Regions table: defines spatial extent of each simulated metro area
CREATE TABLE IF NOT EXISTS regions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  city        TEXT NOT NULL,
  country     TEXT NOT NULL,
  boundary    JSONB NOT NULL,
  population  INTEGER,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Baseline metrics: economic snapshot per region per period
CREATE TABLE IF NOT EXISTS region_baselines (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  region_id       UUID REFERENCES regions(id) ON DELETE CASCADE,
  recorded_at     DATE NOT NULL,
  gdp_index       NUMERIC(10,4),
  unemployment    NUMERIC(5,4),
  real_estate_idx NUMERIC(10,4),
  transit_load    NUMERIC(5,4)
);

-- Simulation runs: persisted after each completed simulation
CREATE TABLE IF NOT EXISTS simulations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  region_id       UUID REFERENCES regions(id),
  params          JSONB NOT NULL,
  horizon_months  INTEGER NOT NULL,
  result_summary  JSONB,
  cell_states     JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_simulations_region ON simulations(region_id);
CREATE INDEX IF NOT EXISTS idx_baselines_region ON region_baselines(region_id);
