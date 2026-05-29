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

from app.db import LOCAL_CASE_STUDIES

CASE_STUDIES: list[dict[str, Any]] = [
    {
        "title": case.title,
        "city": case.city,
        "year": case.year,
        "description": case.description,
        "outcome": case.outcome,
        "source": case.source,
        "tags": case.tags,
        "sectors": case.sectors,
        "policies": case.policies,
    }
    for case in LOCAL_CASE_STUDIES
]

DEFAULT_MODELS = {
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
    "ollama": "nomic-embed-text",
}


def get_embedding(text: str, provider: str, model: str) -> list[float]:
    if provider == "gemini":
        from google import genai

        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        result = client.models.embed_content(model=model, contents=text)
        return result.embeddings[0].values

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
