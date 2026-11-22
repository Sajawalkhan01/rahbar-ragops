"""Command line for Part A.

    python -m ragops.ingestion run --inbox data/inbox/batch_a      # verify + incremental ingest
    python -m ragops.ingestion quarantine list|show <file>|release <file>
    python -m ragops.ingestion audit                                # orphan / missing-chunk check
    python -m ragops.ingestion rollback --family fee-structure --to 2026-27
    python -m ragops.ingestion status                               # ledger summary

`run`, `rollback` need RAGOPS_ROLE=ingestor (the only writer to the vector store).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.config import get_settings

from ragops import vectorstore
from ragops.config import get_paths, load_yaml
from ragops.embedding import embed_documents, embed_model_version

from .incremental import Ingestor
from .state import Ledger, Quarantine


def _ingestor(args: argparse.Namespace, client) -> Ingestor:  # type: ignore[no-untyped-def]
    settings = get_settings()
    paths = get_paths().ensure()
    vcfg = load_yaml(args.config)
    version = embed_model_version(settings.ollama_url, settings.embed_model)
    return Ingestor(paths, vcfg, settings, client, lambda t: embed_documents(t, settings), version)


def cmd_run(args: argparse.Namespace) -> int:
    paths = get_paths().ensure()
    try:
        with vectorstore.writer(paths.state) as client:
            ing = _ingestor(args, client)
            if args.rebuild:
                try:
                    client.delete_collection(ing.settings.collection)
                except Exception:   # nothing to delete
                    pass
                ing.ledger.data["documents"] = {}
            out = ing.run(Path(args.inbox), origin=args.origin, snapshot=not args.no_snapshot,
                          move_quarantined=not args.keep_inbox, label=args.label)
    except (vectorstore.WriterNotAllowed, vectorstore.WriterBusy) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 3
    rep = out["report"]
    print(json.dumps({k: rep[k] for k in (
        "run_id", "documents_seen", "chunks_embedded", "chunks_in_collection", "index_changed")}))
    return 0


def cmd_quarantine(args: argparse.Namespace) -> int:
    q = Quarantine(get_paths().quarantine)
    if args.action == "list":
        for e in q.entries():
            print(f"{e['file']:45} {','.join(e['categories']):28} run={e['run_id']}")
            for r in e["reasons"]:
                print(f"    - {r}")
    elif args.action == "show":
        for e in q.entries():
            if args.target in (e["file"], e["doc_id"], e["sha256"]):
                print(json.dumps(e, indent=2))
                return 0
        print("not in quarantine", file=sys.stderr)
        return 1
    elif args.action == "release":
        print(json.dumps(q.release(args.target, args.note), indent=2))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    ing = _ingestor(args, vectorstore.get_reader())
    result = ing.audit()
    print(json.dumps(result, indent=2))
    return 0 if result["consistent"] else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    paths = get_paths().ensure()
    with vectorstore.writer(paths.state) as client:
        print(json.dumps(_ingestor(args, client).rollback(args.family, args.to), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    settings = get_settings()
    ledger = Ledger(get_paths().state / f"ledger.{settings.collection}.json")
    print(f"{'doc_id':48} {'family':22} {'version':9} {'status':9} chunks")
    for r in sorted(ledger.records(include_deleted=True), key=lambda r: (r["family"], r["doc_version"])):
        print(f"{r['doc_id']:48} {r['family']:22} {r['doc_version']:9} {r['status']:9} {r['chunk_count']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ragops.ingestion")
    p.add_argument("--config", default="verification.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--inbox", required=True)
    r.add_argument("--origin")
    r.add_argument("--label", default="")
    r.add_argument("--no-snapshot", action="store_true", help="do not delete documents missing from the inbox")
    r.add_argument("--keep-inbox", action="store_true", help="copy (not move) quarantined files")
    r.add_argument("--rebuild", action="store_true", help="drop the collection and re-embed everything")
    r.set_defaults(fn=cmd_run)
    q = sub.add_parser("quarantine")
    q.add_argument("action", choices=["list", "show", "release"])
    q.add_argument("target", nargs="?", default="")
    q.add_argument("--note", default="")
    q.set_defaults(fn=cmd_quarantine)
    sub.add_parser("audit").set_defaults(fn=cmd_audit)
    b = sub.add_parser("rollback")
    b.add_argument("--family", required=True)
    b.add_argument("--to", required=True)
    b.set_defaults(fn=cmd_rollback)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = p.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
