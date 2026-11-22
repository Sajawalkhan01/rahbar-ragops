"""C2: the release gate. Reads REAL result files and a thresholds file; returns PASS or FAIL.

    python experiments/release_gate.py --baseline eval/results/suite-baseline-*.json \
        --candidate eval/results/suite-cand-*.json [--thresholds config/release_thresholds.yaml]

Exit code 0 = every rule passed (release allowed), 1 = at least one rule failed (reject).
Thresholds come from the config file only. On Kubernetes that file is the ConfigMap
`release-thresholds`, so editing the ConfigMap changes the verdict without rebuilding the image.
Two kinds of rule: `vs_baseline` (a candidate may not be worse than the baseline by more than X) and
`absolute` (a floor or ceiling that holds regardless of the baseline).
"""

from __future__ import annotations

import json
from typing import Any


def metrics_of(result: dict[str, Any]) -> dict[str, float | None]:
    run = result["runs"][0]
    rc = run["retrieval"]["clean"]["metrics"]
    gm = run["generation"]["metrics"]
    lat = run["generation"]["latency_ms"]
    return {"recall@3": rc["recall@3"], "recall@5": rc["recall@5"], "mrr": rc["mrr"], "ndcg@5": rc["ndcg@5"],
            "faithfulness": gm["faithfulness"], "answer_correctness": gm["answer_correctness"],
            "citation_validity": gm["citation_validity"], "abstention_correctness": gm["abstention_correctness"],
            "p50_ms": lat["p50"], "p95_ms": lat["p95"]}


def _rule(name: str, value: float | None, op: str, limit: float, detail: str) -> dict[str, Any]:
    ok = value is not None and (value >= limit if op == ">=" else value <= limit)
    return {"rule": name, "value": None if value is None else round(value, 4), "op": op,
            "limit": round(limit, 4), "passed": ok, "detail": detail}


def apply_gate(baseline: dict[str, Any], candidate: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    b, c = metrics_of(baseline), metrics_of(candidate)
    vb, ab = thresholds.get("vs_baseline", {}), thresholds.get("absolute", {})
    rules = []
    if "max_recall5_drop" in vb:
        rules.append(_rule("recall@5 vs baseline", c["recall@5"], ">=", b["recall@5"] - vb["max_recall5_drop"],
                           f"baseline {b['recall@5']:.4f}, may drop at most {vb['max_recall5_drop']}"))
    if "max_mrr_drop" in vb:
        rules.append(_rule("MRR vs baseline", c["mrr"], ">=", b["mrr"] - vb["max_mrr_drop"],
                           f"baseline {b['mrr']:.4f}, may drop at most {vb['max_mrr_drop']}"))
    if "max_ndcg5_drop" in vb:
        rules.append(_rule("nDCG@5 vs baseline", c["ndcg@5"], ">=", b["ndcg@5"] - vb["max_ndcg5_drop"],
                           f"baseline {b['ndcg@5']:.4f}, may drop at most {vb['max_ndcg5_drop']}"))
    if "max_answer_correctness_drop" in vb:
        rules.append(_rule("answer correctness vs baseline", c["answer_correctness"], ">=",
                           b["answer_correctness"] - vb["max_answer_correctness_drop"],
                           f"baseline {b['answer_correctness']:.4f}, may drop at most "
                           f"{vb['max_answer_correctness_drop']}"))
    if "min_abstention_delta" in vb:
        rules.append(_rule("abstention correctness vs baseline", c["abstention_correctness"], ">=",
                           b["abstention_correctness"] + vb["min_abstention_delta"],
                           f"baseline {b['abstention_correctness']:.4f}, must not be lower"))
    if "min_faithfulness" in ab:
        rules.append(_rule("faithfulness", c["faithfulness"], ">=", ab["min_faithfulness"], "absolute floor"))
    if "min_citation_validity" in ab:
        rules.append(_rule("citation validity", c["citation_validity"], ">=", ab["min_citation_validity"],
                           "absolute floor"))
    if "min_answer_correctness" in ab:
        rules.append(_rule("answer correctness", c["answer_correctness"], ">=", ab["min_answer_correctness"],
                           "absolute floor"))
    if "max_p95_latency_ms" in ab:
        rules.append(_rule("p95 latency (ms)", c["p95_ms"], "<=", ab["max_p95_latency_ms"], "absolute ceiling"))
    return {"passed": all(r["passed"] for r in rules), "baseline_label": baseline.get("label"),
            "candidate_label": candidate.get("label"), "baseline_metrics": b, "candidate_metrics": c,
            "thresholds": thresholds, "rules": rules}


def print_report(report: dict[str, Any]) -> None:
    print(f"\nRELEASE GATE   baseline={report['baseline_label']}   candidate={report['candidate_label']}")
    print(f"{'rule':38} {'candidate':>10}  {'need':>14}  result   detail")
    for r in report["rules"]:
        need = f"{r['op']} {r['limit']}"
        print(f"{r['rule']:38} {str(r['value']):>10}  {need:>14}  {'PASS' if r['passed'] else 'FAIL':6}   {r['detail']}")
    print("\nGATE: " + ("PASS - release allowed" if report["passed"] else "FAIL - release rejected"))


def load(path: str) -> dict[str, Any]:
    return json.loads(open(path, encoding="utf-8").read())
