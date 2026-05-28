-- MetroPulse Database Schema
-- Migration 005: Fix simulations.region_id to accept city name strings
-- The app stores city name strings (e.g. "hyderabad") not UUID FK references,
-- because region data comes from YAML files, not the regions table.

-- Drop the FK constraint
ALTER TABLE simulations DROP CONSTRAINT IF EXISTS simulations_region_id_fkey;

-- Change region_id from UUID to TEXT so city name strings work directly
ALTER TABLE simulations ALTER COLUMN region_id TYPE TEXT;
