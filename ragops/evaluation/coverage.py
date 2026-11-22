"""Part E: does the golden set still represent real usage? (paper 4.2.7, assignment E2-E4)

    python -m ragops.evaluation.coverage --label before          # exit 1 when coverage < required share
    python -m ragops.evaluation.coverage --label after

For every live query the most similar golden question is found (cosine similarity of `search_query:`
embeddings, the same query embedder the API uses). A live query is COVERED when that similarity reaches the
threshold. Coverage is the covered share; the paper's example flags a gap when fewer than 85% reach the
score (config/evaluation.yaml: coverage.threshold and coverage.required_share, both overridable on the
command line). Uncovered queries are grouped into topics: greedy clustering of their embeddings, each group
named by its most frequent content words. The command exits 1 when coverage is below the required share, so
it can sit in a pipeline next to the release gate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from ragops.config import ROOT, get_paths, load_yaml

EmbedQueries = Callable[[list[str]], list[list[float]]]


def _unit(vectors: list[list[float]]) -> np.ndarray:
    m = np.asarray(vectors, dtype=np.float64)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)


def _keywords(texts: list[str], n: int = 4) -> list[str]:
    from app.retrieval.bm25 import tokenize

    counts: Counter[str] = Counter()
    for t in texts:
        counts.update(set(tokenize(t)))
    return [w for w, _ in counts.most_common(n)]


def compute(golden: list[dict[str, Any]], live: list[dict[str, Any]], embed: EmbedQueries,
            threshold: float, required_share: float, topic_similarity: float = 0.80) -> dict[str, Any]:
    g_vec = _unit(embed([q["question"] for q in golden]))
    l_vec = _unit(embed([q["query"] for q in live]))
    sims = l_vec @ g_vec.T
    best = sims.argmax(axis=1)
    rows = []
    for i, q in enumerate(live):
        score = float(sims[i, best[i]])
        rows.append({"id": q.get("id", f"l{i + 1:02d}"), "query": q["query"], "domain": q.get("domain"),
                     "best_golden_id": golden[best[i]]["id"], "best_golden_question": golden[best[i]]["question"],
                     "similarity": round(score, 4), "covered": score >= threshold})
    covered = [r for r in rows if r["covered"]]
    uncovered = [r for r in rows if not r["covered"]]
    # group the uncovered queries into topics: each joins the first group whose seed it resembles
    groups: list[dict[str, Any]] = []
    u_idx = [i for i, r in enumerate(rows) if not r["covered"]]
    for i in u_idx:
        for g in groups:
            if float(l_vec[i] @ l_vec[g["seed"]]) >= topic_similarity:
                g["members"].append(i)
                break
        else:
            groups.append({"seed": i, "members": [i]})
    topics = [{"topic_keywords": _keywords([rows[i]["query"] for i in g["members"]]),
               "size": len(g["members"]), "queries": [rows[i]["query"] for i in g["members"]]}
              for g in sorted(groups, key=lambda g: -len(g["members"]))]
    share = len(covered) / len(rows) if rows else 0.0
    in_domain = [r for r in rows if r["domain"] is True]
    return {
        "threshold": threshold, "required_share": required_share, "golden_questions": len(golden),
        "live_queries": len(rows), "covered": len(covered), "uncovered": len(uncovered),
        "coverage": round(share, 4), "meets_requirement": share >= required_share,
        "in_domain_coverage": round(sum(r["covered"] for r in in_domain) / len(in_domain), 4) if in_domain else None,
        "similarity_stats": {"mean": round(float(np.mean([r["similarity"] for r in rows])), 4),
                             "p10": round(float(np.percentile([r["similarity"] for r in rows], 10)), 4),
                             "median": round(float(np.median([r["similarity"] for r in rows])), 4)},
        "uncovered_topics": topics, "per_query": rows,
    }


def default_embedder() -> EmbedQueries:
    from app.retrieval.embedder import OllamaEmbedder
    from pipeline.config import get_settings

    s = get_settings()
    e = OllamaEmbedder(s.ollama_url, s.embed_model, timeout=60)
    return lambda texts: [e.embed_query(t) for t in texts]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def markdown(r: dict[str, Any], label: str) -> str:
    lines = [f"# Query coverage: {label}", "",
             f"{r['live_queries']} live queries vs {r['golden_questions']} golden questions | similarity threshold "
             f"**{r['threshold']}** | required share {r['required_share']:.0%}", "",
             f"**Coverage {r['coverage']:.1%}** ({r['covered']} covered, {r['uncovered']} uncovered) -> "
             f"{'OK' if r['meets_requirement'] else 'BELOW THE REQUIRED SHARE'}", ""]
    if r["in_domain_coverage"] is not None:
        lines += [f"In-domain queries only: {r['in_domain_coverage']:.1%}", ""]
    lines += ["## Uncovered topics", ""]
    for t in r["uncovered_topics"]:
        lines.append(f"* **{', '.join(t['topic_keywords'])}** ({t['size']} queries)")
        for q in t["queries"]:
            lines.append(f"  * {q}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    cfg = load_yaml("evaluation.yaml")["coverage"]
    ev = load_yaml("evaluation.yaml")
    ap = argparse.ArgumentParser(prog="ragops.evaluation.coverage")
    ap.add_argument("--golden", default=str(ROOT / ev["golden"]))
    ap.add_argument("--live", default=str(ROOT / cfg["live_queries"]))
    ap.add_argument("--threshold", type=float, default=cfg["threshold"])
    ap.add_argument("--required-share", type=float, default=cfg["required_share"])
    ap.add_argument("--label", default="coverage")
    ap.add_argument("--out-dir")
    args = ap.parse_args(argv)
    golden, live = load_jsonl(Path(args.golden)), load_jsonl(Path(args.live))
    result = compute(golden, live, default_embedder(), args.threshold, args.required_share)
    result.update({"label": args.label, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "golden_file": args.golden, "live_file": args.live})
    out = Path(args.out_dir) if args.out_dir else get_paths().results
    out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    (out / f"coverage-{args.label}-{stamp}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    text = markdown(result, args.label)
    (out / f"coverage-{args.label}-{stamp}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["meets_requirement"] else 1


if __name__ == "__main__":
    sys.exit(main())
