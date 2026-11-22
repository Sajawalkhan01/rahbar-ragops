"""Discovering the documents of an incoming batch and reading their metadata.

Metadata comes from, in increasing priority:
  1. the A2 manifest `_index.json` in the inbox (name, url, fetched_at, doc_version, superseded),
  2. front matter in .md/.txt files (`key: value` lines between `---` markers),
  3. a sidecar `<file>.meta.json`.
A field that none of them supplies stays missing, and the completeness check reports it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED = {".pdf", ".md", ".txt", ".html", ".htm"}
SKIP_NAMES = {"_index.json", "manifest.md", "readme.md"}


def slug(name: str) -> str:
    """The same slug A2's chunker uses for chunk ids (indexer/pipeline/chunk.py `_slug`)."""
    stem = name.rsplit(".", 1)[0]
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:60] or "doc"


def doc_id_for(file_name: str) -> str:
    return slug(file_name)


@dataclass
class DocInput:
    path: Path
    file: str
    sha256: str
    size: int
    origin: str                                  # inbox name, e.g. batch_a
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        return doc_id_for(self.file)

    @property
    def family(self) -> str:
        return str(self.meta.get("doc_family") or self.doc_id)

    @property
    def declared_superseded(self) -> bool:
        return bool(self.meta.get("superseded", False))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_front_matter(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip():
            meta[key.strip()] = _coerce(value.strip())
    return meta


def _coerce(value: str) -> Any:
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"\d+", value):
        return int(value)
    return value


def _manifest(inbox: Path) -> dict[str, dict[str, Any]]:
    index = inbox / "_index.json"
    if not index.exists():
        return {}
    try:
        entries = json.loads(index.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        meta = {
            "title": e.get("title") or e.get("name"),
            "source": e.get("source") or e.get("url"),
            "date": e.get("date") or e.get("fetched_at"),
            "doc_version": e.get("doc_version"),
            "superseded": e.get("superseded"),
            "doc_family": e.get("doc_family"),
            "pages": e.get("pages"),
        }
        out[e["file"]] = {k: v for k, v in meta.items() if v not in (None, "")}
    return out


def discover(inbox: Path, origin: str | None = None) -> list[DocInput]:
    """Every supported file in the inbox, sorted by name (so runs are deterministic)."""
    origin = origin or inbox.name
    manifest = _manifest(inbox)
    docs: list[DocInput] = []
    for path in sorted(inbox.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        if path.name.lower() in SKIP_NAMES or path.name.startswith("."):
            continue
        meta = dict(manifest.get(path.name, {}))
        if path.suffix.lower() in (".md", ".txt"):
            meta.update({k: v for k, v in read_front_matter(path).items() if v not in (None, "")})
        sidecar = path.with_name(path.name + ".meta.json")
        if sidecar.exists():
            meta.update(json.loads(sidecar.read_text(encoding="utf-8")))
        docs.append(DocInput(path=path, file=path.name, sha256=file_sha256(path),
                             size=path.stat().st_size, origin=origin, meta=meta))
    return docs
