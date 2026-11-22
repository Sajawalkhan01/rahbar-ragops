"""D2: the trace tool. Takes a trace id and prints what produced that answer, from the STORED trace only.

    python -m ragops.tracing.inspector <trace_id> [--dir traces/logs] [--json] [--prompt-only]

The context and prompt are rebuilt from the passages stored in the trace with the same function the
generator used (app.services.prompt.build_messages); the rebuilt prompt's hash is compared with the
hash recorded at query time, so a match proves the printed prompt is the one the model saw.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.schemas import Passage
from app.services.prompt import build_messages
from app.tracing import prompt_hash


def trace_dir(arg: str | None) -> Path:
    return Path(arg or os.environ.get("RAGOPS_TRACE_DIR") or os.environ.get("TRACE_DIR") or "traces/logs")


def iter_traces(directory: Path):  # type: ignore[no-untyped-def]
    for path in sorted(directory.glob("**/*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def find_trace(directory: Path, trace_id: str) -> dict[str, Any] | None:
    matches = [t for t in iter_traces(directory) if t.get("trace_id", "").startswith(trace_id)]
    if len(matches) > 1:
        raise SystemExit(f"{len(matches)} traces start with {trace_id!r}; give more characters")
    return matches[0] if matches else None


def rebuild_prompt(trace: dict[str, Any]) -> tuple[list[dict[str, str]], list[Passage]]:
    text_by_id = {c["chunk_id"]: c["text"] for c in trace.get("context", [])}
    passages = [Passage(chunk_id=r["chunk_id"], text=text_by_id.get(r["chunk_id"], ""), source=r["source"],
                        section=r["section"], page=r.get("page"), score=r["score"],
                        doc_version=r.get("doc_version", ""), superseded=r.get("superseded", False))
                for r in trace.get("retrieved", [])]
    return build_messages(trace["query"], passages), passages


def render(trace: dict[str, Any], prompt_only: bool = False) -> str:
    out: list[str] = []
    w = out.append
    messages, _ = rebuild_prompt(trace) if trace.get("retrieved") else ([], [])
    if prompt_only:
        for m in messages:
            w(f"--- {m['role']} ---\n{m['content']}")
        return "\n".join(out)
    w(f"TRACE {trace['trace_id']}   {trace['timestamp']}   request_id={trace.get('request_id', '-')}")
    w("=" * 100)
    w(f"Query            : {trace['query']}")
    if trace.get("rewritten_query"):
        w(f"Rewritten query  : {trace['rewritten_query']}")
    w(f"Collection       : {trace.get('collection', '-')}  (index_id {str(trace.get('index_id', '-'))[:12]}, "
      f"version {trace.get('collection_version', '-')})")
    w(f"Embedding model  : {trace.get('embedding_model', '-')}  version {trace.get('embedding_model_version', '-')}")
    w(f"Filters applied  : {trace.get('filters')}   (older versions included: {trace.get('include_older_versions')})")
    w(f"Cache            : {trace.get('cache')}")
    m = trace.get("model", {})
    w(f"Model/params     : {m}")
    w("")
    w("RETRIEVED (final order given to the generator)")
    w(f"  {'#':>2} {'score':>7}  {'chunk_id':34} {'doc_id':28} {'version':8} {'sup':5} page  section")
    for r in trace.get("retrieved", []):
        w(f"  {r['rank']:>2} {r['score']:>7.4f}  {r['chunk_id']:34} {r['doc_id'][:28]:28} "
          f"{r['doc_version']:8} {str(r['superseded']):5} {str(r['page']):4}  {r['section'][:40]}")
    if trace.get("dense_order"):
        w("  dense order (before fusion): " + ", ".join(f"{d['chunk_id']}={d['similarity']}" for d in trace["dense_order"]))
        w("  fused order (after RRF)    : " + ", ".join(f"{d['chunk_id']}={d['rrf']}" for d in trace["fused_order"]))
    w("")
    w("GUARDRAILS")
    for g in trace.get("guardrails", []) or [{"action": "(none)"}]:
        w("  - " + ", ".join(f"{k}={v}" for k, v in g.items()))
    w("")
    if messages:
        recorded = trace.get("prompt_hash")
        rebuilt = prompt_hash(messages)
        w(f"PROMPT   recorded hash {str(recorded)[:16]}...  rebuilt hash {rebuilt[:16]}...  "
          f"=> {'MATCH' if recorded == rebuilt else 'MISMATCH' if recorded else 'no hash recorded (abstained before generation)'}")
        w("CONTEXT given to the generator (after the injection filter):")
        w(messages[1]["content"])
        w("")
    r = trace.get("response", {})
    w("ANSWER")
    w(f"  {r.get('answer')}")
    w(f"  answered_from_context={r.get('answered_from_context')} confidence={r.get('confidence')} "
      f"cached={r.get('cached')} invalid_citations_removed={r.get('invalid_citations_removed')}")
    w("CITATIONS")
    for c in trace.get("citations", []) or ["(none)"]:
        w(f"  - {c}")
    w("")
    w("LATENCY per stage (ms): " + ", ".join(f"{k}={v}" for k, v in trace.get("latency_ms", {}).items()))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ragops.tracing.inspector")
    ap.add_argument("trace_id")
    ap.add_argument("--dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--prompt-only", action="store_true")
    args = ap.parse_args(argv)
    trace = find_trace(trace_dir(args.dir), args.trace_id)
    if trace is None:
        print(f"no trace starting with {args.trace_id!r} in {trace_dir(args.dir)}", file=sys.stderr)
        return 1
    print(json.dumps(trace, indent=2, ensure_ascii=False) if args.json else render(trace, args.prompt_only))
    return 0


if __name__ == "__main__":
    sys.exit(main())
