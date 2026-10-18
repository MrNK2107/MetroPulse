CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS twin_places (
  place_id text PRIMARY KEY,
  level text NOT NULL,
  lgd_code text,
  name text NOT NULL,
  parent_id text,
  state_code text,
  boundary_version text NOT NULL,
  geom geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS twin_indicators (
  id text PRIMARY KEY,
  name text,
  description text,
  unit text,
  domains text[],
  source_id text
);

CREATE INDEX IF NOT EXISTS twin_places_geom_gix ON twin_places USING GIST (geom);
