"""
Seed case_studies table with urban policy case study data and embeddings.

Supports OpenAI, Google Gemini, and Ollama embedding providers.
Set EMBEDDING_PROVIDER env var to "openai", "gemini", or "ollama".
Set EMBEDDING_MODEL to override the default model per provider.

Usage:
    set LLM_PROVIDER=ollama && python scripts/seed_case_studies.py
"""
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

CASE_STUDIES: list[dict[str, Any]] = [
    {
        "title": "NYC Tech Sector Boom 2012-2019",
        "city": "New York",
        "year": 2019,
        "description": (
            "New York City experienced a sustained technology sector boom from 2012 to 2019, "
            "driven by FDI in tech infrastructure and tax incentives. Employment in tech "
            "grew by 40%, real estate prices in Manhattan rose 35%, and transit congestion "
            "increased 22% on key subway lines. The boom disproportionately affected "
            "neighborhoods in Lower Manhattan and Brooklyn, with ripple effects up to 5km "
            "from major tech hub concentrations."
        ),
        "tags": ["tech_boom", "fdi_positive", "real_estate", "congestion"],
    },
    {
        "title": "Detroit Manufacturing Decline 2008-2014",
        "city": "Detroit",
        "year": 2014,
        "description": (
            "Detroit's automotive manufacturing sector experienced a severe FDI contraction "
            "during and after the 2008 financial crisis. Manufacturing FDI dropped by 60%, "
            "leading to a 25% unemployment rate, 50% decline in real estate values, and "
            "widespread urban decay. Employment elasticity in manufacturing was estimated "
            "at 0.55, with each percentage point of FDI decline producing 0.8% job loss "
            "in directly affected census tracts."
        ),
        "tags": ["manufacturing_decline", "fdi_negative", "unemployment", "urban_decay"],
    },
    {
        "title": "London Crossrail Public Works Impact",
        "city": "London",
        "year": 2022,
        "description": (
            "The Elizabeth Line (Crossrail) public works project in London demonstrated "
            "the cascading effects of transit infrastructure investment. Property values "
            "within 1km of new stations increased by 25-30% within 2 years of opening. "
            "Commercial real estate saw a 40% premium in station-adjacent zones. "
            "The distance decay function showed benefits dropping to 5% beyond 3.5km "
            "from station locations."
        ),
        "tags": ["public_works", "transit", "real_estate", "infrastructure"],
    },
    {
        "title": "Shenzhen SEZ Transformation",
        "city": "Shenzhen",
        "year": 2020,
        "description": (
            "Shenzhen's transformation from a fishing village to a global tech hub "
            "illustrates extreme FDI-driven urban metamorphosis. Over 40 years, "
            "tech FDI averaging +15% annually produced GDP growth of 20% per year. "
            "Real estate values increased 100x. The case demonstrates that sustained "
            "positive FDI across all sectors produces non-linear compounding effects, "
            "with manufacturing FDI providing the initial employment base before tech "
            "FDI drives higher-value economic activity."
        ),
        "tags": ["tech_boom", "manufacturing", "fdi_positive", "long_term"],
    },
    {
        "title": "San Francisco Housing Crisis 2015-2020",
        "city": "San Francisco",
        "year": 2020,
        "description": (
            "San Francisco experienced a tech FDI surge (+60% in tech sector investment) "
            "that produced severe negative externalities. While GDP grew 35%, real estate "
            "index reached 2.4x baseline, pricing out essential workers. Transit congestion "
            "increased 40%. The case highlights that tech FDI without corresponding "
            "manufacturing or infrastructure investment creates asymmetric growth patterns "
            "affecting lower-income neighborhoods most severely within 2-4km of tech hubs."
        ),
        "tags": ["tech_boom", "fdi_positive", "inequality", "housing_crisis"],
    },
    {
        "title": "Tokyo Public Works and Zoning Reform 2000-2010",
        "city": "Tokyo",
        "year": 2010,
        "description": (
            "Tokyo's coordinated public works program combined with zoning liberalization "
            "demonstrated effective urban policy. Mixed-sector FDI (+5-10% annually) "
            "combined with targeted infrastructure spending within 2km zones produced "
            "balanced growth: 15% GDP increase, stable unemployment at 3.5%, and "
            "manageable congestion (+8%). The case supports the model where public works "
            "boost multipliers of 0.3 within 2km produce optimal cascade effects."
        ),
        "tags": ["public_works", "balanced_growth", "zoning", "fdi_moderate"],
    },
]

DEFAULT_MODELS = {
    "openai": "text-embedding-3-small",
    "gemini": "text-embedding-004",
    "ollama": "nomic-embed-text",
}


def get_embedding(text: str, provider: str, model: str) -> list[float]:
    if provider == "gemini":
        import google.generativeai as genai

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        result = genai.embed_content(model=model, content=text)
        return result["embedding"]

    elif provider == "ollama":
        import httpx

        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        resp = httpx.post(
            f"{base_url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    else:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.embeddings.create(input=text, model=model)
        return response.data[0].embedding


def main() -> None:
    provider = os.environ.get("EMBEDDING_PROVIDER") or os.environ.get("LLM_PROVIDER") or "openai"
    model = os.environ.get("EMBEDDING_MODEL") or DEFAULT_MODELS.get(provider, "text-embedding-3-small")

    api_key_map = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }

    if provider in api_key_map:
        key = os.environ.get(api_key_map[provider])
        if not key:
            print(f"Warning: {api_key_map[provider]} not set. Embeddings will be placeholder zeros.")
            print(f"Run: set {api_key_map[provider]}=...")
            provider = "none"

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Warning: SUPABASE_URL or SUPABASE_KEY not set. Printing seed data to stdout.")

    for cs in CASE_STUDIES:
        if provider != "none":
            try:
                cs["embedding"] = get_embedding(cs["description"], provider, model)
                print(f"  Embedded: {cs['title']} ({provider}/{model})")
            except Exception as e:
                print(f"  Embedding failed for {cs['title']}: {e}")
                cs["embedding"] = [0.0] * 1536
        else:
            cs["embedding"] = [0.0] * 1536

    if not supabase_url or not supabase_key:
        print(json.dumps(CASE_STUDIES, indent=2))
    else:
        print(f"Prepared {len(CASE_STUDIES)} case studies for insertion.")
        print("To insert, connect to Supabase and run the INSERT statements.")


if __name__ == "__main__":
    main()
