-- MetroPulse Database Schema
-- Migration 004: pgvector match function for semantic case study search

CREATE OR REPLACE FUNCTION match_case_studies(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  filter_city text DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  city TEXT,
  year INTEGER,
  description TEXT,
  tags TEXT[],
  outcome TEXT,
  source TEXT,
  sectors TEXT[],
  policies TEXT[],
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    cs.id,
    cs.title,
    cs.city,
    cs.year,
    cs.description,
    cs.tags,
    cs.outcome,
    cs.source,
    cs.sectors,
    cs.policies,
    1 - (cs.embedding <=> query_embedding) AS similarity
  FROM case_studies cs
  WHERE cs.embedding IS NOT NULL
    AND (filter_city IS NULL OR cs.city ILIKE '%' || filter_city || '%')
  ORDER BY cs.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
