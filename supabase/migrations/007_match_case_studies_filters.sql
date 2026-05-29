-- Migration 007: add strict filter arguments to semantic case-study search.

CREATE OR REPLACE FUNCTION match_case_studies(
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  filter_city text DEFAULT NULL,
  filter_sectors text[] DEFAULT NULL,
  filter_policies text[] DEFAULT NULL
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
    AND (filter_sectors IS NULL OR cs.sectors && filter_sectors)
    AND (filter_policies IS NULL OR cs.policies && filter_policies)
  ORDER BY cs.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
