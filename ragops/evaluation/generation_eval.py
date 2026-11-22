"""B3, end-to-end level: is the final answer right, grounded, cited, and does it abstain correctly?

Runs A2's full `answer_question` (retrieve, relevance floor, generate, validate, citation check) on
every applicable golden question, in process, and reads each query's trace.

Metrics
  answer_correctness       the expected key phrase appears in the answer (answerable + hard questions)
  faithfulness             share of answer sentences supported by the retrieved context: a sentence is
                           supported when >= `support_threshold` of its content words occur in the
                           context. Lexical, deterministic, no judge model. See the report for why it is
                           the metric least to be trusted.
  citation_validity        A2's metric: citations that match a retrieved passage / all citations
  abstention_correctness   share of unanswerable questions that were declined
  false_abstention_rate    share of answerable questions that were wrongly declined
  latency p50 / p95        wall-clock milliseconds of the whole query pipeline, plus per stage (traces)
"""

from __future__ import annotations

import re
import time
from typing import Any

from app import tracing
from app.retrieval.bm25 import tokenize
from app.services.answer import answer_question

from .common import citation_counts, latency_summary

_SENT = re.compile(r"(?<=[.!?])\s+")


def norm(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").split())


def contains_expected(answer: str, expect: str | None) -> bool:
    if not expect:
        return False
    a, e = norm(answer), norm(expect)
    return e in a or e.replace(",", "") in a.replace(",", "")


def faithfulness(answer: str, context: str, threshold: float) -> float:
    ctx = set(tokenize(context))
    sentences = [s for s in _SENT.split(answer) if tokenize(s)]
    if not sentences:
        return 0.0
    ok = sum(1 for s in sentences if len(set(tokenize(s)) & ctx) / len(set(tokenize(s))) >= threshold)
    return ok / len(sentences)


def run(retriever, provider, settings, golden: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    thr = cfg["generation"]["support_threshold"]
    answer_question("What is the tuition fee?", retriever, provider, settings)   # warm-up (model load)
    rows: list[dict[str, Any]] = []
    for q in golden:
        t0 = time.perf_counter()
        response = answer_question(q["question"], retriever, provider, settings)
        wall_ms = (time.perf_counter() - t0) * 1000
        trace = tracing.last_trace() or {}
        retrieved = [{"source": r.source, "section": r.section, "page": r.page, "score": r.score}
                     for r in response.retrieved]
        context = " ".join(c["text"] for c in trace.get("context", []))
        valid, total = citation_counts(response.model_dump())
        answered = bool(response.answered_from_context)
        rows.append({
            "id": q["id"], "type": q["type"], "category": q["category"], "question": q["question"],
            "must_abstain": bool(q.get("must_abstain")), "answered": answered,
            "answer": response.answer, "expect": q.get("expect"),
            "correct": contains_expected(response.answer, q.get("expect")) if answered else False,
            "faithfulness": round(faithfulness(response.answer, context, thr), 4) if answered else None,
            "citations_valid": valid, "citations_total": total,
            "top1_score": retrieved[0]["score"] if retrieved else None,
            "latency_ms": round(wall_ms, 2), "stage_ms": trace.get("latency_ms", {}),
            "trace_id": trace.get("trace_id"), "guardrails": [g["action"] for g in trace.get("guardrails", [])],
            "drifted": bool(q.get("drifted")),
        })
    pos = [r for r in rows if not r["must_abstain"]]
    neg = [r for r in rows if r["must_abstain"]]
    answered_pos = [r for r in pos if r["answered"]]
    cite_total = sum(r["citations_total"] for r in rows)
    stage_names = sorted({k for r in rows for k in r["stage_ms"]})
    metrics = {
        "answer_correctness": round(sum(r["correct"] for r in pos) / len(pos), 4) if pos else None,
        "faithfulness": round(sum(r["faithfulness"] for r in answered_pos) / len(answered_pos), 4)
        if answered_pos else None,
        "citation_validity": round(sum(r["citations_valid"] for r in rows) / cite_total, 4) if cite_total else None,
        "abstention_correctness": round(sum(not r["answered"] for r in neg) / len(neg), 4) if neg else None,
        "false_abstention_rate": round(sum(not r["answered"] for r in pos) / len(pos), 4) if pos else None,
    }
    return {
        "questions": len(rows), "answerable_or_hard": len(pos), "unanswerable": len(neg),
        "metrics": metrics,
        "latency_ms": latency_summary([r["latency_ms"] for r in rows]),
        "latency_ms_per_stage": {s: latency_summary([r["stage_ms"][s] for r in rows if s in r["stage_ms"]])
                                 for s in stage_names},
        "wrong_or_abstained": [r["id"] for r in pos if not r["correct"]],
        "wrongly_answered_unanswerable": [r["id"] for r in neg if r["answered"]],
        "per_question": rows,
    }
