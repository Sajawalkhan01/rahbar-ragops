"""B1, module level: is the embedding model any good for this domain, and is it repeatable?

Measures, with the SAME embedding call the indexer uses (pipeline.embed, `search_document:` prefix):
  * mean cosine similarity of paraphrase pairs vs unrelated pairs, and the gap between them
    (a useful model has a large gap; the gap, not the absolute value, is what matters)
  * embedding time per chunk, on real chunks sampled from the live collection
  * determinism: the same text embedded twice, largest absolute difference of any component
"""

from __future__ import annotations

import json
import random
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np
from pipeline.config import get_settings as indexer_settings

from ragops.embedding import embed_documents


def cosine(a: list[float], b: list[float]) -> float:
    x, y = np.asarray(a), np.asarray(b)
    return float(x @ y / ((np.linalg.norm(x) * np.linalg.norm(y)) or 1.0))


def evaluate(pairs_path: Path, sample_texts: list[str], seed: int, repeats: int = 2) -> dict[str, Any]:
    settings = indexer_settings()
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"embedding_model": settings.embed_model}
    for kind in ("paraphrase", "unrelated"):
        texts = [t for pair in pairs[kind] for t in pair]
        vecs = embed_documents(texts, settings)
        sims = [cosine(vecs[i], vecs[i + 1]) for i in range(0, len(vecs), 2)]
        out[kind] = {"pairs": len(sims), "mean_cosine": round(statistics.fmean(sims), 4),
                     "min": round(min(sims), 4), "max": round(max(sims), 4),
                     "scores": [round(s, 4) for s in sims]}
    out["gap"] = round(out["paraphrase"]["mean_cosine"] - out["unrelated"]["mean_cosine"], 4)
    out["separation_check"] = {
        "min_paraphrase_above_max_unrelated": out["paraphrase"]["min"] > out["unrelated"]["max"],
        "overlap_note": "True means every paraphrase pair scored higher than every unrelated pair"}
    # time per chunk (one request per chunk, like a single query at serving time)
    rng = random.Random(seed)
    sample = rng.sample(sample_texts, min(20, len(sample_texts))) if sample_texts else []
    times = []
    for text in sample:
        t0 = time.perf_counter()
        embed_documents([text], settings)
        times.append((time.perf_counter() - t0) * 1000)
    out["time_per_chunk_ms"] = {"n": len(times), "mean": round(statistics.fmean(times), 1) if times else None,
                                "p50": round(statistics.median(times), 1) if times else None,
                                "max": round(max(times), 1) if times else None,
                                "note": "single-chunk requests, CPU, after a warm-up call"}
    # determinism
    probe = (sample or [p[0] for p in pairs["paraphrase"]])[:5]
    diffs = []
    for text in probe:
        first = np.asarray(embed_documents([text], settings)[0])
        for _ in range(repeats - 1):
            again = np.asarray(embed_documents([text], settings)[0])
            diffs.append(float(np.max(np.abs(first - again))))
    out["determinism"] = {"texts": len(probe), "repeats": repeats,
                          "max_abs_difference": max(diffs) if diffs else None,
                          "deterministic": bool(diffs) and max(diffs) == 0.0}
    return out
