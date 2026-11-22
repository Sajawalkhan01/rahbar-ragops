"""Shared pieces of the evaluation suite: the golden set, the in-process pipeline, the metrics.

The pipeline under test is A2's, unchanged: `ChromaRetriever` + `answer_question` + an LLM provider.
It is called in-process (no HTTP), which lets the suite read each query's trace and time each stage.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import platform
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from ragops.config import ROOT

# A2's scoring functions are the evaluation (eval/run_eval.py); reuse, do not copy.
sys.path.insert(0, str(ROOT / "eval"))
from run_eval import _matches, citation_counts  # type: ignore[import-not-found]  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402


# ------------------------------------------------------------------ golden set
def load_golden(path: str | Path, state: str) -> list[dict[str, Any]]:
    """The questions that apply to `state` ('A' = Batch A only, 'AB' = Batch A and B ingested).
    In state AB a question may carry `after_batch_b` ground truth that replaces its own (drift)."""
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    out = []
    for r in rows:
        if r.get("requires_batch") == "B" and state != "AB":
            continue
        r = dict(r)
        if state == "AB" and r.get("after_batch_b"):
            r.update(r["after_batch_b"])
            r["drifted"] = True
        out.append(r)
    return out


def detect_state(collection: Any) -> str:
    """AB when the Batch B newer fee version is in the collection, else A."""
    rows = collection.get(where={"doc_id": "fee-structure-2027-28"}, limit=1, include=[])
    return "AB" if rows["ids"] else "A"


# ------------------------------------------------------------------ pipeline construction
def make_settings(overrides: dict[str, Any] | None = None) -> Settings:
    """Settings from the environment (the same variables the API reads) plus experiment overrides."""
    base = get_settings()
    valid = {f.name for f in dataclasses.fields(Settings)}
    clean = {k: v for k, v in (overrides or {}).items() if k in valid}
    return dataclasses.replace(base, retriever="chroma", cache_enabled=False, **clean)


def make_pipeline(settings: Settings, client: Any = None):  # type: ignore[no-untyped-def]
    from app.providers.llm import get_provider
    from app.retrieval.chroma import ChromaRetriever

    if client is None:
        from ragops.vectorstore import get_reader
        client = get_reader()
    return ChromaRetriever(settings, client=client), get_provider(settings)


def embed_model_version(settings: Settings) -> str:
    from ragops.embedding import embed_model_version as v
    return v(settings.ollama_url, settings.embed_model)


def run_environment(settings: Settings, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """What the result file records so a run can be reproduced (assignment B4)."""
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "embedding_model": settings.embed_model, "embedding_model_version": embed_model_version(settings),
        "llm_provider": settings.llm_provider, "llm_model": settings.llm_model,
        "temperature": settings.temperature, "top_k": settings.top_k, "hybrid": settings.hybrid,
        "relevance_floor": settings.relevance_floor, "collection": settings.collection,
        "candidate_pool": settings.candidate_pool, "rrf_k": settings.rrf_k,
        "ollama_url_host": re.sub(r"^https?://", "", settings.ollama_url),
        "pod": os.environ.get("HOSTNAME", "local"), **(extra or {}),
    }


# ------------------------------------------------------------------ retrieval metrics
def _first_hits(relevant: list[dict[str, Any]], retrieved: list[dict[str, Any]]) -> list[int | None]:
    """For each relevant entry, the 1-based rank of the first passage that matches it (or None)."""
    ranks: list[int | None] = []
    for rel in relevant:
        rank = next((i for i, got in enumerate(retrieved, start=1) if _matches(rel, got)), None)
        ranks.append(rank)
    return ranks


def retrieval_scores(relevant: list[dict[str, Any]], retrieved: list[dict[str, Any]],
                     ks: tuple[int, ...] = (3, 5), ndcg_k: int = 5) -> dict[str, float]:
    ranks = _first_hits(relevant, retrieved)
    out: dict[str, float] = {}
    for k in ks:
        out[f"recall@{k}"] = sum(1 for r in ranks if r is not None and r <= k) / len(relevant)
    found = [r for r in ranks if r is not None]
    out["mrr"] = 1.0 / min(found) if found else 0.0
    dcg = sum(1.0 / math.log2(r + 1) for r in found if r <= ndcg_k)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), ndcg_k) + 1))
    out[f"ndcg@{ndcg_k}"] = dcg / ideal if ideal else 0.0
    return out


def mean_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = rows[0].keys() if rows else []
    return {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in keys}


# ------------------------------------------------------------------ latency
def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo), 3)


def latency_summary(values_ms: list[float]) -> dict[str, float | None]:
    return {"n": len(values_ms), "p50": percentile(values_ms, 0.5), "p95": percentile(values_ms, 0.95),
            "mean": round(statistics.fmean(values_ms), 3) if values_ms else None,
            "max": round(max(values_ms), 3) if values_ms else None}


def retrieved_dicts(passages: list[Any]) -> list[dict[str, Any]]:
    return [{"source": p.source, "section": p.section, "page": p.page, "chunk_id": p.chunk_id,
             "score": round(p.score, 4)} for p in passages]


def now_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


__all__ = ["citation_counts", "load_golden", "detect_state", "make_settings", "make_pipeline",
           "retrieval_scores", "mean_metrics", "latency_summary", "run_environment", "now_stamp"]
