"""Embedding helpers shared by ingestion and evaluation: A2's embedder, plus counting and versions."""

from __future__ import annotations

import httpx
from pipeline.config import IndexerSettings
from pipeline.embed import embed as a2_embed


def embed_documents(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    """A2's indexer embedding call (adds the `search_document:` prefix)."""
    return a2_embed(texts, settings)


def embed_model_version(ollama_url: str, model: str) -> str:
    """The model's content digest as Ollama reports it (first 12 hex chars), or 'unknown'."""
    try:
        tags = httpx.get(f"{ollama_url.rstrip('/')}/api/tags", timeout=10).json().get("models", [])
        for m in tags:
            if m.get("name", "").split(":")[0] == model.split(":")[0]:
                return str(m.get("digest", "unknown"))[:12]
    except (httpx.HTTPError, ValueError):
        pass
    return "unknown"
