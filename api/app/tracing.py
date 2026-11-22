"""Per-query trace records (Assignment 03, Part D1; paper 3.2.3 and 5.1).

Every call of `answer_question` produces ONE JSON line that lets you reconstruct what happened:
the query, what was retrieved (chunk ids, document ids, versions, scores), the filters, the order
before and after fusion, the exact context given to the generator (and a hash of the prompt),
model parameters, the answer and citations, every guardrail action, latency per stage and the
cache result. The line goes to standard output (so `kubectl logs` shows it) and, when TRACE_DIR is
set, to a JSONL file on the traces volume (one file per pod, so replicas never interleave writes).

Nothing here logs secrets: the settings object is never dumped, only named model parameters.

How it is wired: `begin()` starts a trace in a context variable; the retriever, the prompt builder
and the answer service call `note()`, `guardrail()` and `stage()`, which do nothing when no trace
is active (unit tests, other callers). `finish()` writes the line.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from contextvars import ContextVar
from pathlib import Path
from typing import Any

_current: ContextVar[dict[str, Any] | None] = ContextVar("rahbar_trace", default=None)
_file_lock = threading.Lock()
_last: dict[str, Any] | None = None   # the most recently finished trace (used by the evaluation suite)


def last_trace() -> dict[str, Any] | None:
    return _last


def enabled() -> bool:
    return os.environ.get("TRACE_ENABLED", "true").lower() not in ("0", "false", "no")


def begin(query: str, **fields: Any) -> dict[str, Any] | None:
    """Start a trace for this request and return it (None when tracing is switched off)."""
    if not enabled():
        _current.set(None)
        return None
    trace: dict[str, Any] = {
        "type": "trace",
        "trace_id": uuid.uuid4().hex,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time() * 1000) % 1000:03d}Z",
        "query": query,
        "rewritten_query": None,
        "retrieved": [],
        "filters": None,
        "guardrails": [],
        "latency_ms": {},
        "cache": "bypass",
        "_t0": time.perf_counter(),
        **fields,
    }
    _current.set(trace)
    return trace


def active() -> dict[str, Any] | None:
    return _current.get()


def note(**fields: Any) -> None:
    trace = _current.get()
    if trace is not None:
        trace.update(fields)


def guardrail(action: str, **detail: Any) -> None:
    """Record one guardrail decision and its reason."""
    trace = _current.get()
    if trace is not None:
        entry = {"action": action, **detail}
        if entry not in trace["guardrails"]:      # the prompt may be rendered twice (hash, then provider)
            trace["guardrails"].append(entry)


@contextlib.contextmanager
def stage(name: str) -> Iterator[None]:
    """Time a pipeline stage; the milliseconds land in latency_ms[name]."""
    start = time.perf_counter()
    try:
        yield
    finally:
        trace = _current.get()
        if trace is not None:
            trace["latency_ms"][name] = round(trace["latency_ms"].get(name, 0.0)
                                              + (time.perf_counter() - start) * 1000, 2)


def prompt_hash(messages: list[dict[str, str]]) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def finish(**fields: Any) -> dict[str, Any] | None:
    """Close the active trace, write it, and return the finished record."""
    trace = _current.get()
    if trace is None:
        return None
    trace.update(fields)
    global _last
    trace["latency_ms"]["total"] = round((time.perf_counter() - trace.pop("_t0")) * 1000, 2)
    _current.set(None)
    _last = trace
    line = json.dumps(trace, ensure_ascii=False, default=str)
    if os.environ.get("TRACE_STDOUT", "true").lower() not in ("0", "false", "no"):
        print(line, file=sys.stdout, flush=True)
    directory = os.environ.get("TRACE_DIR")
    if directory:
        try:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            name = f"traces-{os.environ.get('HOSTNAME', 'local')}-{time.strftime('%Y%m%d', time.gmtime())}.jsonl"
            with _file_lock, (path / name).open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass   # a full or read-only volume must never fail a user's request
    return trace
