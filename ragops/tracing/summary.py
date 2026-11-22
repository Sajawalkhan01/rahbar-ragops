"""D3: summarise a trace log over a time window.

    python -m ragops.tracing.summary [--dir traces/logs] [--since 24h] [--out traces/metrics/summary.json]

Reports: top-1 retrieval similarity distribution, abstention rate, cache hit rate, p50/p95 latency per
stage, number of injection attempts flagged (question and passage), plus pipeline-health counters
(fallbacks, removed citations). The same numbers are exposed live as Prometheus metrics at /metrics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from .inspector import iter_traces, trace_dir


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo), 3)


def parse_since(text: str) -> float:
    m = re.fullmatch(r"(\d+)([smhd])", text)
    if not m:
        raise SystemExit("--since must look like 90m, 24h or 7d")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def parse_ts(ts: str) -> float:
    return time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone


def summarise(traces: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(traces)
    tops = [t["retrieved"][0]["score"] for t in traces if t.get("retrieved")]
    abstained = sum(1 for t in traces if not t.get("response", {}).get("answered_from_context", True))
    lookups = [t for t in traces if t.get("cache") in ("hit", "miss")]
    hits = sum(1 for t in lookups if t["cache"] == "hit")
    stages: dict[str, list[float]] = {}
    for t in traces:
        for k, v in t.get("latency_ms", {}).items():
            stages.setdefault(k, []).append(v)
    flags: dict[str, int] = {}
    for t in traces:
        for g in t.get("guardrails", []):
            flags[g["action"]] = flags.get(g["action"], 0) + 1
    buckets = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    hist = {f"{a:.1f}-{min(b, 1.0):.1f}": sum(1 for s in tops if a <= s < b) for a, b in zip(buckets, buckets[1:])}
    return {
        "queries": n,
        "top1_similarity": {"count": len(tops), "mean": round(sum(tops) / len(tops), 4) if tops else None,
                            "p10": quantile(tops, 0.1), "p50": quantile(tops, 0.5), "p90": quantile(tops, 0.9),
                            "histogram": hist},
        "abstention_rate": round(abstained / n, 4) if n else None,
        "cache": {"lookups": len(lookups), "hits": hits,
                  "hit_rate": round(hits / len(lookups), 4) if lookups else None,
                  "bypassed": n - len(lookups)},
        "latency_ms_per_stage": {k: {"p50": quantile(v, 0.5), "p95": quantile(v, 0.95), "n": len(v)}
                                 for k, v in sorted(stages.items())},
        "guardrail_actions": dict(sorted(flags.items())),
        "injection_attempts_flagged": flags.get("question_injection_flagged", 0)
                                      + flags.get("injection_sentence_removed", 0),
        "health": {"fallback_answers": flags.get("fallback_answer", 0),
                   "citations_removed": flags.get("citations_removed", 0),
                   "queries_without_retrieval": sum(1 for t in traces if not t.get("retrieved"))},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ragops.tracing.summary")
    ap.add_argument("--dir")
    ap.add_argument("--since", default="")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    traces = list(iter_traces(trace_dir(args.dir)))
    if args.since:
        cutoff = time.time() - parse_since(args.since)
        traces = [t for t in traces if parse_ts(t["timestamp"]) >= cutoff]
    result = {"window": args.since or "all", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              **summarise(traces)}
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
