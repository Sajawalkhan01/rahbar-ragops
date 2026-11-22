"""Persistent state of the RAGOps layer: the document ledger, the quarantine and the archive.

All three live on the data volume (a PVC on Kubernetes), so they survive pod restarts.

  ledger.json            one record per document: hashes, version, status, chunk ids, history
  quarantine/            rejected files, plus quarantine_log.jsonl (why each was rejected)
  archive/<doc>/<ver>/   superseded or deleted versions, kept so a rollback can restore them
  datalake/<doc>/<ver>/  the accepted raw file (the data lake of paper Figure 3)
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from ragops.config import Paths

from .documents import DocInput


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Ledger:
    """JSON file with an atomic write (write to a temp file, then rename)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {"schema": 1, "documents": {}, "runs": []}
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))

    @property
    def docs(self) -> dict[str, dict[str, Any]]:
        return self.data["documents"]

    def records(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        return [d for d in self.docs.values() if include_deleted or d["status"] != "deleted"]

    def get(self, doc_id: str) -> dict[str, Any] | None:
        return self.docs.get(doc_id)

    def put(self, record: dict[str, Any]) -> None:
        self.docs[record["doc_id"]] = record

    def event(self, doc_id: str, event: str, detail: str = "") -> None:
        self.docs[doc_id].setdefault("history", []).append({"ts": now(), "event": event, "detail": detail})

    def family_members(self, family: str) -> list[dict[str, Any]]:
        return [d for d in self.records() if d["family"] == family]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)


class Quarantine:
    """Rejected documents and the reason for each. A quarantined file is never indexed."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log_path = root / "quarantine_log.jsonl"

    def _events(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines() if line]

    def add(self, inp: DocInput, record: dict[str, Any], run_id: str, move: bool = True) -> Path:
        dest_dir = self.root / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / inp.file
        if move and inp.path.exists():
            shutil.move(str(inp.path), dest)
            for extra in (inp.path.with_name(inp.file + ".meta.json"),):
                if extra.exists():
                    shutil.move(str(extra), dest_dir / extra.name)
        else:
            shutil.copy2(inp.path, dest)
        entry = {"event": "quarantined", "ts": now(), "run_id": run_id, "doc_id": inp.doc_id,
                 "file": inp.file, "sha256": inp.sha256, "stored_at": str(dest.relative_to(self.root)),
                 "categories": record["categories"], "reasons": record["failure_reasons"],
                 "recommended_action": record["recommended_action"]}
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return dest

    def entries(self) -> list[dict[str, Any]]:
        """Current quarantine entries (a release event cancels the matching quarantine)."""
        active: dict[str, dict[str, Any]] = {}
        for e in self._events():
            if e["event"] == "quarantined":
                active[e["sha256"]] = e
            elif e["event"] == "released":
                active.pop(e["sha256"], None)
        return list(active.values())

    def blocked(self) -> dict[str, dict[str, Any]]:
        """Files that must not be re-submitted unchanged, keyed by SHA-256.

        A document rejected only as a DUPLICATE is not blocked: its bytes equal the original's, so blocking
        the hash would also block the original (found by running Batch B, then the incremental demo, in which
        library-rules.md was skipped because library-rules-copy.md had been quarantined)."""
        return {e["sha256"]: e for e in self.entries()
                if not all(c.startswith("duplicate") for c in e["categories"])}

    def is_quarantined(self, sha256: str) -> dict[str, Any] | None:
        return self.blocked().get(sha256)

    def release(self, file_or_sha: str, note: str = "") -> dict[str, Any]:
        """Lift the block on one entry so the file can be resubmitted. Never indexes anything itself."""
        for e in self.entries():
            if file_or_sha in (e["file"], e["sha256"], e["doc_id"]):
                with self.log_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"event": "released", "ts": now(), "sha256": e["sha256"],
                                         "file": e["file"], "note": note}) + "\n")
                return e
        raise KeyError(f"{file_or_sha} is not in quarantine")


def datalake_path(paths: Paths, doc_id: str, version: str, file: str) -> Path:
    return paths.datalake / doc_id / str(version) / file


def archive_path(paths: Paths, doc_id: str, version: str, file: str) -> Path:
    return paths.archive / doc_id / str(version) / file


def store_file(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest
