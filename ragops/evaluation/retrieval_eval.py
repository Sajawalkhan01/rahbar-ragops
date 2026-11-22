"""B2, component level: does the retriever put the right passage in the top k?

recall@3, recall@5, MRR and nDCG@5 against the golden set, measured on A2's own `ChromaRetriever`
(hybrid dense + BM25 + exact-term fusion, version filter). Ground truth is matched by (source, page or
section), as in A2's eval/run_eval.py, so the golden set survives re-chunking.

Noise test (two kinds, both reported against the clean run):
  irrelevant documents: four campus documents about other things (cafeteria, sports, alumni dinner,
                        Wi-Fi) are chunked, embedded and added to a PRIVATE in-memory copy of the
                        collection. The live collection is never written.
  typos:                a seeded share of the query words gets one character edit.
"""

from __future__ import annotations

import dataclasses
import random
from pathlib import Path
from typing import Any

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import get_settings as indexer_settings
from pipeline.extract import extract

from app.config import Settings
from app.retrieval.chroma import ChromaRetriever
from ragops.embedding import embed_documents

from .common import mean_metrics, retrieval_scores, retrieved_dicts
from .memstore import MemoryClient

POOL = 10   # retrieve this many so MRR can see beyond rank 5


def typo_query(text: str, rate: float, rng: random.Random) -> str:
    """One character edit (swap, drop, or double) in a seeded share of the words longer than 3 letters."""
    words = text.split()
    for i, w in enumerate(words):
        core = [j for j, c in enumerate(w) if c.isalpha()]
        if len(core) <= 3 or rng.random() > rate:
            continue
        j = rng.choice(core[1:-1] or core)
        kind = rng.choice(["swap", "drop", "double"])
        if kind == "swap" and j + 1 < len(w):
            w = w[:j] + w[j + 1] + w[j] + w[j + 2:]
        elif kind == "drop":
            w = w[:j] + w[j + 1:]
        else:
            w = w[:j] + w[j] + w[j:]
        words[i] = w
    return " ".join(words)


def evaluate(retriever: ChromaRetriever, golden: list[dict[str, Any]], k_values: tuple[int, ...],
             ndcg_k: int, query_fn=lambda q: q) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    rows, per_q = [], []
    for q in golden:
        if not q.get("relevant"):
            continue
        query = query_fn(q["question"])
        passages = retriever.retrieve(query, k=POOL)
        got = retrieved_dicts(passages)
        scores = retrieval_scores(q["relevant"], got, k_values, ndcg_k)
        rows.append(scores)
        per_q.append({"id": q["id"], "type": q["type"], "category": q["category"], "query": query,
                      **{k: round(v, 4) for k, v in scores.items()},
                      "top1": {"chunk_id": got[0]["chunk_id"], "source": got[0]["source"],
                               "page": got[0]["page"], "section": got[0]["section"][:50],
                               "score": got[0]["score"]} if got else None})
    by_type: dict[str, Any] = {}
    for t in sorted({r["type"] for r in per_q}):
        by_type[t] = mean_metrics([{k: v for k, v in r.items() if k in rows[0]} for r in per_q if r["type"] == t])
    return {"questions": len(rows), "metrics": mean_metrics(rows), "by_type": by_type, "per_question": per_q}


def noise_client(retriever: ChromaRetriever, noise_dir: Path, settings: Settings) -> tuple[ChromaRetriever, int]:
    """A retriever over an in-memory copy of the collection plus the noise documents."""
    source = retriever.collection()
    client, coll = MemoryClient.copy_of(source, "noise")
    isettings = indexer_settings()
    added = 0
    for path in sorted(noise_dir.glob("*.md")):
        doc = extract(str(path), "2026", False)
        pieces = chunk(clean(doc), isettings.chunk_size, isettings.chunk_overlap)
        vectors = embed_documents([p.text for p in pieces], isettings)
        for p, v in zip(pieces, vectors):
            coll.add(f"noise-{p.id}", p.text, {**p.metadata(), "doc_id": f"noise-{path.stem}"}, v)
            added += 1
    noisy = ChromaRetriever(dataclasses.replace(settings, collection="noise"), client=client,
                            embedder=retriever.embedder)
    return noisy, added


def run(retriever: ChromaRetriever, golden: list[dict[str, Any]], settings: Settings, cfg: dict[str, Any],
        seed: int) -> dict[str, Any]:
    ks, nk = tuple(cfg["k_values"]), cfg["ndcg_k"]
    clean_result = evaluate(retriever, golden, ks, nk)
    noisy, added = noise_client(retriever, Path(cfg["noise"]["irrelevant_docs_dir"]), settings)
    docs_result = evaluate(noisy, golden, ks, nk)
    rng = random.Random(seed)
    typo_result = evaluate(retriever, golden, ks, nk,
                           query_fn=lambda q: typo_query(q, cfg["noise"]["typo_rate"], rng))
    delta = lambda a, b: {k: round(b["metrics"][k] - a["metrics"][k], 4) for k in a["metrics"]}  # noqa: E731
    return {
        "clean": clean_result,
        "noise_irrelevant_docs": {**docs_result, "irrelevant_chunks_added": added,
                                  "irrelevant_documents": len(list(Path(cfg["noise"]["irrelevant_docs_dir"]).glob("*.md")))},
        "noise_typos": {**typo_result, "typo_rate": cfg["noise"]["typo_rate"]},
        "delta_vs_clean": {"irrelevant_docs": delta(clean_result, docs_result),
                           "typos": delta(clean_result, typo_result)},
    }
