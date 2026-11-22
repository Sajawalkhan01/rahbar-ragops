"""Extraction for the verification stage: A2's `pipeline.extract` plus a cache and error capture.

Why a cache: OCR of the scanned A2 PDFs takes 15 to 30 minutes. The cache is keyed by the file's
SHA-256, so it can never serve text for a changed file. A2's own `_extracted/<file>.json` files
(written by eval/chunk_experiment.py) seed it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.models import Document, Page

from .documents import DocInput


@dataclass
class Extraction:
    document: Document | None
    error: str = ""
    seconds: float = 0.0
    from_cache: bool = False
    text: str = field(default="", repr=False)

    @property
    def ok(self) -> bool:
        return self.document is not None and not self.error


def _to_json(doc: Document) -> dict:
    return {"source": doc.source, "doc_version": doc.doc_version, "superseded": doc.superseded,
            "problems": doc.problems,
            "pages": [{"page": p.page, "text": p.text, "ocr": p.ocr} for p in doc.pages]}


def _from_json(data: dict, version: str, superseded: bool) -> Document:
    doc = Document(source=data["source"], doc_version=version, superseded=superseded,
                   problems=list(data.get("problems", [])))
    doc.pages = [Page(data["source"], p["page"], p["text"], bool(p.get("ocr", False)))
                 for p in data["pages"]]
    return doc


def extract_document(inp: DocInput, cache_dir: Path) -> Extraction:
    from pipeline.extract import extract

    version = str(inp.meta.get("doc_version") or inp.meta.get("date") or "unknown")
    superseded = inp.declared_superseded
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{inp.sha256}.json"
    seed = inp.path.parent / "_extracted" / f"{inp.file}.json"
    for candidate in (cached, seed):
        if candidate.exists():
            try:
                doc = _from_json(json.loads(candidate.read_text(encoding="utf-8")), version, superseded)
                if candidate is seed and not cached.exists():
                    cached.write_text(json.dumps(_to_json(doc)), encoding="utf-8")
                return Extraction(doc, from_cache=True, text=_text(doc))
            except (json.JSONDecodeError, KeyError, OSError):
                continue
    started = time.perf_counter()
    try:
        doc = extract(str(inp.path), version, superseded)
    except Exception as exc:   # corrupt or truncated PDF, unsupported type, unreadable bytes
        return Extraction(None, error=f"{type(exc).__name__}: {str(exc)[:200]}",
                          seconds=time.perf_counter() - started)
    cached.write_text(json.dumps(_to_json(doc)), encoding="utf-8")
    return Extraction(doc, seconds=time.perf_counter() - started, text=_text(doc))


def _text(doc: Document) -> str:
    return "\n\n".join(p.text for p in doc.pages)
