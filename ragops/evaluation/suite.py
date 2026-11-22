"""The Part B suite: ONE command, timestamped result file, summary table.

    python -m ragops.evaluation.suite --label baseline
    python -m ragops.evaluation.suite --label cand --experiment experiments/candidate/c1.yaml \
        --gate-against eval/results/suite-baseline-*.json          # exits 1 when the release gate fails

Runs, per repetition: module level (embedding), component level (retrieval + noise), end-to-end level
(answers). The whole suite runs `--repeat` times (default 2) with the same seed, and the result file
reports the difference per metric (assignment B4). Every result file records the models and versions,
the configuration and the seed.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

from ragops.config import ROOT, get_paths, load_yaml

from . import embedding_eval, generation_eval, retrieval_eval
from .common import (detect_state, load_golden, make_pipeline, make_settings, now_stamp,
                     run_environment)


def flatten(prefix: str, node: Any, out: dict[str, float]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("per_question", "scores", "histogram", "per_question_ids"):
                continue
            flatten(f"{prefix}.{k}" if prefix else k, v, out)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out[prefix] = float(node)


def one_run(settings, golden, cfg, seed: int, sample_texts: list[str]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    random.seed(seed)
    # A fresh retriever per run: A2's retriever keeps an LRU cache of query embeddings, which would make
    # the second run look faster than the first for a reason that has nothing to do with the pipeline.
    retriever, provider = make_pipeline(settings)
    t0 = time.perf_counter()
    result = {
        "embedding": embedding_eval.evaluate(ROOT / cfg["embedding"]["paraphrase_pairs"], sample_texts, seed,
                                             cfg["embedding"]["determinism_repeats"]),
        "retrieval": retrieval_eval.run(retriever, [q for q in golden], settings, cfg, seed),
        "generation": generation_eval.run(retriever, provider, settings, golden, cfg),
    }
    result["seconds"] = round(time.perf_counter() - t0, 1)
    return result


def summary_rows(run: dict[str, Any]) -> list[tuple[str, str, str]]:
    e, r, g = run["embedding"], run["retrieval"], run["generation"]
    rc, nd, nt = r["clean"]["metrics"], r["noise_irrelevant_docs"]["metrics"], r["noise_typos"]["metrics"]
    gm, lat = g["metrics"], g["latency_ms"]
    f = lambda v: "n/a" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))  # noqa: E731
    rows = [
        ("Module: embedding", "mean cosine, paraphrase pairs", f(e["paraphrase"]["mean_cosine"])),
        ("", "mean cosine, unrelated pairs", f(e["unrelated"]["mean_cosine"])),
        ("", "gap (paraphrase - unrelated)", f(e["gap"])),
        ("", "time per chunk (mean ms)", f(e["time_per_chunk_ms"]["mean"])),
        ("", "determinism: max abs difference", f(e["determinism"]["max_abs_difference"])),
        ("Component: retrieval", "recall@3 / recall@5", f"{f(rc['recall@3'])} / {f(rc['recall@5'])}"),
        ("", "MRR / nDCG@5", f"{f(rc['mrr'])} / {f(rc['ndcg@5'])}"),
        ("", "noise: irrelevant docs, recall@5 / MRR / nDCG@5", f"{f(nd['recall@5'])} / {f(nd['mrr'])} / {f(nd['ndcg@5'])}"),
        ("", "noise: typos, recall@5 / MRR / nDCG@5", f"{f(nt['recall@5'])} / {f(nt['mrr'])} / {f(nt['ndcg@5'])}"),
        ("End-to-end: answers", "answer correctness", f(gm["answer_correctness"])),
        ("", "faithfulness (lexical support)", f(gm["faithfulness"])),
        ("", "citation validity", f(gm["citation_validity"])),
        ("", "abstention correctness / false abstentions", f"{f(gm['abstention_correctness'])} / {f(gm['false_abstention_rate'])}"),
        ("", "latency p50 / p95 (ms)", f"{f(lat['p50'])} / {f(lat['p95'])}"),
    ]
    return rows


def markdown(result: dict[str, Any]) -> str:
    run1 = result["runs"][0]
    lines = [f"# Evaluation suite: {result['label']}", "",
             f"{result['timestamp']} | state **{result['state']}** | collection `{result['environment']['collection']}` "
             f"| provider `{result['environment']['llm_provider']}` | top_k {result['environment']['top_k']} "
             f"| seed {result['seed']} | {result['golden_questions']} golden questions | {len(result['runs'])} runs", "",
             "| Level | Metric | Value (run 1) |", "| --- | --- | --- |"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in summary_rows(run1)]
    sto = result["stochasticity"]
    lines += ["", f"## Run-to-run difference ({len(result['runs'])} runs, same seed)", "",
              f"Largest absolute difference over {sto['metrics_compared']} quality metrics: "
              f"**{sto['max_abs_diff_quality']}**. Latency and timing metrics differ naturally.", "",
              "| Metric | run 1 | run 2 | abs diff |", "| --- | --- | --- | --- |"]
    for k, v in sto["largest"][:8]:
        lines.append(f"| {k} | {v['run1']} | {v['run2']} | {v['abs_diff']} |")
    g = run1["generation"]
    lines += ["", f"Wrong or abstained answerable questions: {g['wrong_or_abstained'] or 'none'}",
              f"Unanswerable questions that were answered: {g['wrongly_answered_unanswerable'] or 'none'}"]
    return "\n".join(lines) + "\n"


def stochasticity(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) < 2:
        return {"metrics_compared": 0, "max_abs_diff_quality": None, "largest": []}
    a, b = {}, {}
    flatten("", {k: v for k, v in runs[0].items() if k != "seconds"}, a)
    flatten("", {k: v for k, v in runs[1].items() if k != "seconds"}, b)
    timing = ("latency", "time_per_chunk", ".seconds", "p50", "p95", ".mean", ".max")
    diffs = {}
    for k in a:
        if k in b:
            diffs[k] = {"run1": round(a[k], 4), "run2": round(b[k], 4), "abs_diff": round(abs(a[k] - b[k]), 4)}
    quality = {k: v for k, v in diffs.items() if not any(t in k for t in timing)}
    ranked = sorted(diffs.items(), key=lambda kv: -kv[1]["abs_diff"])
    return {"metrics_compared": len(quality),
            "max_abs_diff_quality": max((v["abs_diff"] for v in quality.values()), default=0.0),
            "quality_metrics_with_any_difference": {k: v for k, v in quality.items() if v["abs_diff"] > 0},
            "largest": ranked[:12]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ragops.evaluation.suite")
    ap.add_argument("--label", default="run")
    ap.add_argument("--config", default="evaluation.yaml")
    ap.add_argument("--experiment", help="YAML of settings overrides (collection, top_k, relevance_floor, ...)")
    ap.add_argument("--state", default="auto", choices=["auto", "A", "AB"])
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--provider")
    ap.add_argument("--limit", type=int, help="only the first N golden questions (live-LLM spot check)")
    ap.add_argument("--gate-against", help="baseline result file: apply the release gate and exit 1 on FAIL")
    ap.add_argument("--thresholds", default="release_thresholds.yaml")
    args = ap.parse_args(argv)

    cfg = load_yaml(args.config)
    exp = load_yaml(args.experiment) if args.experiment else {}
    overrides = {"top_k": cfg["top_k"], "llm_provider": cfg["provider"], "collection": cfg["collection"],
                 **{k: v for k, v in exp.items() if k in ("collection", "top_k", "relevance_floor", "hybrid",
                                                         "candidate_pool", "rrf_k", "temperature")}}
    if exp.get("provider"):
        overrides["llm_provider"] = exp["provider"]
    if os.environ.get("CHROMA_COLLECTION") and not exp.get("collection"):
        overrides["collection"] = os.environ["CHROMA_COLLECTION"]
    if args.provider:
        overrides["llm_provider"] = args.provider
    settings = make_settings(overrides)
    retriever, provider = make_pipeline(settings)
    coll = retriever.collection()
    state = detect_state(coll) if args.state == "auto" else args.state
    golden = load_golden(ROOT / cfg["golden"], state)
    if args.limit:
        golden = golden[: args.limit]
    paths = get_paths()
    os.environ["TRACE_DIR"] = str(paths.traces / "eval")
    os.environ["TRACE_STDOUT"] = "false"
    sample = [t for t in coll.get(limit=200, include=["documents"])["documents"]]

    runs = []
    for i in range(args.repeat):
        print(f"[suite] run {i + 1}/{args.repeat} ...", file=sys.stderr, flush=True)
        runs.append(one_run(settings, golden, cfg, cfg["seed"], sample))
    meta = dict(coll.metadata or {})
    result = {
        "label": args.label, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "state": state, "seed": cfg["seed"], "golden_file": cfg["golden"], "golden_questions": len(golden),
        "config": {"evaluation": cfg, "experiment": exp or None, "overrides": overrides},
        "environment": run_environment(settings, {
            "index_chunk_size": meta.get("chunk_size"), "index_chunk_overlap": meta.get("chunk_overlap"),
            "index_chunks": meta.get("chunks"), "index_embed_model_version": meta.get("embed_model_version"),
            "index_id": meta.get("index_id")}),
        "runs": runs, "stochasticity": stochasticity(runs),
    }
    out_dir = paths.results
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    base = out_dir / f"suite-{args.label}-{stamp}"
    base.with_suffix(".json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    base.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(markdown(result))
    print(f"[suite] wrote {base.with_suffix('.json')}", file=sys.stderr)
    if args.gate_against:
        from ragops.gate import apply_gate, print_report

        report = apply_gate(json.loads(Path(args.gate_against).read_text(encoding="utf-8")), result,
                            load_yaml(args.thresholds))
        print_report(report)
        gate_file = out_dir / f"gate-{args.label}-{stamp}.json"
        gate_file.write_text(json.dumps(report, indent=1), encoding="utf-8")
        return 0 if report["passed"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
