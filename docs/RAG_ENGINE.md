# RAG Engine

> **Status: parked.** This module (`backend/app/rag/`) is not wired into the running app. It was built for the retired city simulator, so the "Primary Loop" and simulation references below describe that older design. The live case-study endpoint is `GET /api/case-studies`; the planning agent queries case studies through its own tool.

The RAG engine supports coefficient reasoning, explanations, and confidence scoring. It does not replace the simulation math and does not invent exact forecasts.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  ParsedScenario  │────▶│  Retriever        │────▶│  EvidencePack        │
│  + scenario_text │     │  (15 case studies) │     │  items + coverage    │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                            │
                                                            ▼
                                                 ┌─────────────────────┐
                                                 │  CoefficientExtractor│
                                                 │  baseline → clamp    │
                                                 └──────────┬──────────┘
                                                            │
                                                            ▼
                                                 ┌─────────────────────┐
                                                 │  Primary Loop        │
                                                 │  K *= adjusted_rate  │
                                                 └─────────────────────┘
```

## Module Files

| File | Responsibility |
|------|---------------|
| `app/rag/models.py` | Pydantic models: EvidenceItem, EvidenceCoverage, EvidencePack, CoefficientAdjustment |
| `app/rag/retriever.py` | Scans LOCAL_CASE_STUDIES, computes relevance scores, filters and sorts |
| `app/rag/evidence_pack.py` | Builds EvidencePack from retriever output with coverage metrics |
| `app/rag/coefficient_extractor.py` | Adjusts sector coefficients within clamps based on evidence strength |
| `app/rag/confidence.py` | Returns overall_evidence_confidence from pack |
| `app/rag/prompts.py` | Policy string for LLM context |

## Evidence Retrieval Flow

1. `retrieve_evidence(parsed, scenario_text, top_k=5)` scans the 15 LOCAL_CASE_STUDIES
2. Computes relevance score per case: city match (0.25) + sector overlap (0.45) + policy overlap (0.20) + keyword match (0.10)
3. Filters out cases with relevance < 0.25
4. Returns sorted list of EvidenceItem objects

## Coefficient Adjustment

The coefficient engine follows a strict pipeline:

| Step | Description |
|------|-------------|
| 1. Baseline | Start from scenario/model baseline coefficient |
| 2. Retrieve | Find relevant evidence items |
| 3. Calculate | `evidence_strength = mean(relevance * confidence)` of matched items |
| 4. Clamp | Factor clamped to [0.65, 1.10] — cannot amplify beyond 10% or reduce below 35% |
| 5. Provenance | Attach sources and reasoning to CoefficientAdjustment |

If no evidence matches, the engine dampens unsupported coefficients rather than inventing stronger effects.

## Evidence Source Types

| Type | Description |
|------|-------------|
| `historical_case_study` | Real Indian urban events (Bengaluru IT, Delhi metro, etc.) |
| `government_report` | Policy documents and government data |
| `research_paper` | Academic studies on urban economics |
| `news_event` | Significant news events with economic impact |
| `policy_document` | Specific policy implementations |
| `manual_seed` | Expert-curated evidence items |

## Integration Points

- **Primary Loop**: `coefficient_factors()` returns per-sector ratios multiplied into `monthly_rate * sector_weight`
- **Tertiary Loop**: Evidence pack included in EVIDENCE WebSocket message
- **Frontend**: Displayed in EvidencePanel "Cases" tab and Technical tab's case retrieval audit
- **Confidence**: `evidence_confidence(pack)` feeds into overall confidence calculation

## Supabase/pgvector (Secondary Path)

The primary retrieval uses keyword/overlap scoring against hardcoded case studies. A secondary path exists for semantic search via Supabase pgvector:

- `db.search_case_studies()` calls the `match_case_studies` RPC function
- `db.seed_case_studies()` upserts the 15 case studies with embeddings
- `db.generate_embedding()` supports OpenAI, Gemini, and Ollama providers
- Fixed 1536 dimensions (CASE_STUDY_EMBEDDING_DIMENSIONS)
