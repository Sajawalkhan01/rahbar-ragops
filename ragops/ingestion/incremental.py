"""A2: incremental ingestion, versioning, deletion and rollback.

One run of `Ingestor.run(inbox)`:

  discover -> classify (unchanged / new-or-changed / previously quarantined)
           -> extract (cached) -> VERIFY (verification.py) -> quarantine the failures
           -> for each accepted document: chunk (A2's chunker), embed ONLY chunks whose text hash
              is new, upsert, delete that document's stale chunks, archive superseded versions
           -> snapshot mode: documents that left the inbox are deleted (chunks removed)
           -> report (counts) and a new collection `index_id` only if something changed.

Chunk metadata carries `doc_id`, `doc_family`, `status`, `text_sha`, `file_sha` next to A2's
`source/section/page/doc_version/superseded`, so the API's existing `superseded == False` filter
is the version filter, and a document's chunks can be counted/deleted by `doc_id`.
This is the ONLY code that writes to Chroma and it runs under vectorstore.writer().
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline.chunk import chunk
from pipeline.clean import clean
from pipeline.config import IndexerSettings
from pipeline.models import Chunk

from ragops.config import Paths

from .documents import DocInput, discover
from .extraction import Extraction, extract_document
from .state import Ledger, Quarantine, archive_path, datalake_path, now, store_file
from .verification import EmbedFn, Known, text_sha256, verify_batch

WRITE_BATCH = 100


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def default_log(msg: str, **fields: Any) -> None:
    print(json.dumps({"ts": now(), "logger": "ragops.ingest", "msg": msg, **fields}, default=str), flush=True)


class Ingestor:
    def __init__(self, paths: Paths, vcfg: dict[str, Any], settings: IndexerSettings, client: Any,
                 embed_fn: EmbedFn, embed_version: str = "unknown",
                 log: Callable[..., None] = default_log) -> None:
        self.paths, self.vcfg, self.settings, self.client = paths, vcfg, settings, client
        self._embed = embed_fn
        self.embed_version = embed_version
        self.log = log
        self.ledger = Ledger(paths.state / f"ledger.{settings.collection}.json")
        self.quarantine = Quarantine(paths.quarantine)
        self.chunks_embedded = 0
        self.doc_embeddings = 0
        self.changed = False

    # ------------------------------------------------------------------ collection helpers
    def _get_collection(self) -> Any | None:
        try:
            return self.client.get_collection(self.settings.collection)
        except Exception:
            return None

    def _open_for_write(self, dimension: int) -> Any:
        coll = self._get_collection()
        if coll is None:
            return self.client.create_collection(name=self.settings.collection,
                                                 metadata={"hnsw:space": "cosine"})
        meta = coll.metadata or {}
        if meta.get("embed_model") not in (None, self.settings.embed_model) or \
                meta.get("dimension") not in (None, dimension):
            raise RuntimeError(
                f"collection {self.settings.collection!r} was built with {meta.get('embed_model')!r}/"
                f"{meta.get('dimension')}, not {self.settings.embed_model!r}/{dimension}: "
                "run with --rebuild to re-embed everything")
        return coll

    def count_by_doc(self, doc_id: str) -> int:
        coll = self._get_collection()
        if coll is None:
            return 0
        return len(coll.get(where={"doc_id": doc_id}, include=[])["ids"])

    def _intact(self, rec: dict[str, Any]) -> bool:
        """The ledger says this document is indexed: does Chroma agree? (self-healing check)"""
        return self.count_by_doc(rec["doc_id"]) == rec["chunk_count"]

    # ------------------------------------------------------------------ the run
    def run(self, inbox: Path, origin: str | None = None, snapshot: bool = True,
            move_quarantined: bool = True, label: str = "") -> dict[str, Any]:
        started = time.perf_counter()
        run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + (f"-{label}" if label else "")
        docs = discover(inbox, origin)
        origin = origin or inbox.name
        blocked = self.quarantine.blocked()
        by_file = {d.file: d for d in docs}

        unchanged: list[DocInput] = []
        todo: list[DocInput] = []
        skipped_quarantined: list[dict[str, Any]] = []
        for d in docs:
            rec = self.ledger.get(d.doc_id)
            if rec and rec["status"] != "deleted" and rec["file_sha"] == d.sha256 and self._intact(rec):
                unchanged.append(d)
            elif d.sha256 in blocked:
                skipped_quarantined.append({"doc_name": d.file, "reason": blocked[d.sha256]["reasons"],
                                            "quarantined_in": blocked[d.sha256]["run_id"]})
            else:
                todo.append(d)
        self.log("ingest start", run_id=run_id, inbox=str(inbox), documents=len(docs),
                 unchanged=len(unchanged), to_verify=len(todo), collection=self.settings.collection)

        # ---- verification (A1) -------------------------------------------------------
        cache = self.paths.state / "extract_cache"
        extractions: dict[str, Extraction] = {d.file: extract_document(d, cache) for d in todo}
        known = self._known({d.doc_id for d in todo})
        records = verify_batch(todo, extractions, self.ledger.records(), known, self._doc_embed,
                               self.vcfg) if todo else []

        new_docs, changed_docs, quarantined, archived_old, indexed = [], [], [], [], []
        for rec in records:
            inp = by_file[rec["doc_name"]]
            if rec["overall"] == "FAIL":
                where = self.quarantine.add(inp, rec, run_id, move=move_quarantined)
                rec["quarantined_to"] = str(where.relative_to(self.paths.data)) \
                    if where.is_relative_to(self.paths.data) else str(where)
                quarantined.append(rec["doc_name"])
                self.log("quarantined", doc=rec["doc_name"], reasons=rec["failure_reasons"])
        for rec in records:
            if rec["overall"] != "PASS":
                continue
            inp = by_file[rec["doc_name"]]
            existed = self.ledger.get(inp.doc_id)
            was_indexed = bool(existed and existed["status"] != "deleted")
            outcome = self._index_document(inp, extractions[inp.file], rec,
                                           archived=bool(rec["superseded_by"]), run_id=run_id)
            if outcome == "empty":      # chunker found no text: reject like a quality failure
                rec["overall"], rec["disposition"] = "FAIL", "quarantine"
                rec["failure_reasons"].append("quality: chunking produced no chunks")
                rec["categories"].append("insufficient")
                self.quarantine.add(inp, rec, run_id, move=move_quarantined)
                quarantined.append(rec["doc_name"])
                continue
            (changed_docs if was_indexed else new_docs).append(inp.file)
            indexed.append(inp.doc_id)
            for old_id in rec["supersedes"]:
                if self._archive_document(old_id, superseded_by=inp.doc_id, run_id=run_id):
                    archived_old.append(old_id)

        # ---- deletions (snapshot mode: the inbox is the full desired state for this origin) --
        deleted: list[str] = []
        orphan_counts: dict[str, int] = {}
        if snapshot:
            present = {d.doc_id for d in docs}
            gone_blocked = {e["doc_id"] for e in self.quarantine.entries()}
            for rec in list(self.ledger.records()):
                if rec.get("origin") == origin and rec["doc_id"] not in present and \
                        rec["doc_id"] not in gone_blocked:
                    self._delete_document(rec["doc_id"], run_id)
                    deleted.append(rec["doc_id"])
                    orphan_counts[rec["doc_id"]] = self.count_by_doc(rec["doc_id"])

        coll = self._get_collection()
        if self.changed and coll is not None:
            self._finalise_collection(coll, run_id)
        report = {
            "run_id": run_id, "timestamp": now(), "inbox": str(inbox), "origin": origin,
            "collection": self.settings.collection, "embed_model": self.settings.embed_model,
            "embed_model_version": self.embed_version,
            "chunk_size": self.settings.chunk_size, "chunk_overlap": self.settings.chunk_overlap,
            "documents_seen": len(docs),
            "unchanged": [d.file for d in unchanged],
            "new": new_docs, "changed": changed_docs, "deleted": deleted,
            "quarantined": quarantined, "skipped_previously_quarantined": skipped_quarantined,
            "archived_superseded_versions": archived_old,
            "chunks_embedded": self.chunks_embedded,
            "document_embeddings_for_near_duplicate_check": self.doc_embeddings,
            "chunks_in_collection": int(coll.count()) if coll is not None else 0,
            "orphan_chunk_counts_after_delete": orphan_counts,
            "index_changed": self.changed,
            "seconds": round(time.perf_counter() - started, 2),
        }
        self.ledger.data["runs"].append({k: report[k] for k in (
            "run_id", "timestamp", "origin", "chunks_embedded", "index_changed")})
        self.ledger.save()
        self._write_reports(run_id, report, records)
        self.log("ingest finished", **{k: v for k, v in report.items()
                                       if k in ("run_id", "documents_seen", "chunks_embedded",
                                                "chunks_in_collection", "index_changed", "seconds")})
        return {"report": report, "records": records}

    # ------------------------------------------------------------------ pieces
    def _doc_embed(self, texts: list[str]) -> list[list[float]]:
        self.doc_embeddings += len(texts)
        return self._embed(texts)

    def _known(self, replacing: set[str]) -> Known:
        known = Known()
        for r in self.ledger.records():
            if r["doc_id"] in replacing:
                continue
            known.add(r["doc_id"], r["family"], r["file_sha"], r.get("text_sha", ""),
                      r.get("doc_embedding"), r.get("sketch"))
        return known

    def _index_document(self, inp: DocInput, ex: Extraction, rec: dict[str, Any], archived: bool,
                        run_id: str) -> str:
        doc = ex.document
        assert doc is not None
        version = str(inp.meta.get("doc_version") or inp.meta.get("date") or "unknown")
        doc.doc_version, doc.superseded = version, archived
        pieces = chunk(clean(doc), self.settings.chunk_size, self.settings.chunk_overlap)
        if not pieces:
            return "empty"
        status = "archived" if archived else "active"
        stamp = now()
        metas = [{**c.metadata(), "doc_id": inp.doc_id, "doc_family": inp.family,
                  "title": str(inp.meta.get("title", "")), "status": status,
                  "text_sha": _sha(c.text), "file_sha": inp.sha256, "ingested_at": stamp}
                 for c in pieces]
        coll = self._get_collection()
        reuse: dict[str, list[float]] = {}
        old_ids: list[str] = []
        if coll is not None:
            existing = coll.get(where={"doc_id": inp.doc_id}, include=["metadatas", "embeddings"])
            old_ids = list(existing["ids"])
            for m, e in zip(existing["metadatas"], existing["embeddings"]):
                reuse[m["text_sha"]] = [float(x) for x in e]
        need = [i for i, m in enumerate(metas) if m["text_sha"] not in reuse]
        fresh = self._embed_chunks([pieces[i].text for i in need])
        vectors: list[list[float]] = []
        fresh_by_index = dict(zip(need, fresh))
        for i, m in enumerate(metas):
            vectors.append(fresh_by_index[i] if i in fresh_by_index else reuse[m["text_sha"]])
        coll = self._open_for_write(len(vectors[0]))
        for s in range(0, len(pieces), WRITE_BATCH):
            part = slice(s, s + WRITE_BATCH)
            coll.upsert(ids=[c.id for c in pieces[part]], documents=[c.text for c in pieces[part]],
                        embeddings=vectors[part], metadatas=metas[part])
        stale = [i for i in old_ids if i not in {c.id for c in pieces}]
        for s in range(0, len(stale), WRITE_BATCH):
            coll.delete(ids=stale[s : s + WRITE_BATCH])
        self.changed = True
        # data lake copy (+ archive copy when indexed as an old version)
        store_file(inp.path, datalake_path(self.paths, inp.doc_id, version, inp.file))
        if archived:
            store_file(inp.path, archive_path(self.paths, inp.doc_id, version, inp.file))
        previous = self.ledger.get(inp.doc_id)
        record = {
            "doc_id": inp.doc_id, "family": inp.family, "file": inp.file, "origin": inp.origin,
            "title": inp.meta.get("title"), "source": inp.meta.get("source"),
            "date": inp.meta.get("date"), "doc_version": version, "status": status,
            "file_sha": inp.sha256, "text_sha": text_sha256(ex.text),
            "doc_embedding": rec.get("doc_embedding"), "sketch": rec.get("sketch"),
            "chunk_ids": [c.id for c in pieces], "chunk_count": len(pieces),
            "chunks_reused": len(pieces) - len(need), "pages": len(doc.pages),
            "ingested_at": stamp, "run_id": run_id,
            "history": previous.get("history", []) if previous else [],
        }
        self.ledger.put(record)
        self.ledger.event(inp.doc_id, "replaced" if previous and previous["status"] != "deleted" else "indexed",
                          f"{len(pieces)} chunks, {len(need)} embedded, {len(pieces) - len(need)} reused, "
                          f"{len(stale)} stale deleted; status={status}")
        self.ledger.save()    # after every document: a crash must not leave Chroma ahead of the ledger
        self.log("indexed", doc=inp.file, chunks=len(pieces), embedded=len(need),
                 reused=len(pieces) - len(need), stale_deleted=len(stale), status=status)
        return "ok"

    def _embed_chunks(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self.chunks_embedded += len(texts)
        return self._embed(texts)

    def _set_status(self, doc_id: str, status: str) -> int:
        """Flip a document's chunks between active and archived (metadata only: no re-embedding)."""
        coll = self._get_collection()
        if coll is None:
            return 0
        rows = coll.get(where={"doc_id": doc_id}, include=["metadatas"])
        if not rows["ids"]:
            return 0
        metas = [{**m, "status": status, "superseded": status != "active"} for m in rows["metadatas"]]
        for s in range(0, len(rows["ids"]), WRITE_BATCH):
            coll.update(ids=rows["ids"][s : s + WRITE_BATCH], metadatas=metas[s : s + WRITE_BATCH])
        self.changed = True
        return len(rows["ids"])

    def _archive_document(self, doc_id: str, superseded_by: str, run_id: str) -> bool:
        rec = self.ledger.get(doc_id)
        if not rec or rec["status"] != "active":
            return False
        n = self._set_status(doc_id, "archived")
        src = datalake_path(self.paths, doc_id, rec["doc_version"], rec["file"])
        if src.exists():
            store_file(src, archive_path(self.paths, doc_id, rec["doc_version"], rec["file"]))
        rec["status"] = "archived"
        rec["superseded_by"] = superseded_by
        self.ledger.event(doc_id, "archived", f"superseded by {superseded_by}; {n} chunks kept, "
                          "excluded from retrieval by metadata superseded=True")
        self.log("archived", doc=doc_id, superseded_by=superseded_by, chunks=n)
        return True

    def _delete_document(self, doc_id: str, run_id: str) -> None:
        rec = self.ledger.docs[doc_id]
        coll = self._get_collection()
        if coll is not None:
            coll.delete(where={"doc_id": doc_id})
            self.changed = True
        src = datalake_path(self.paths, doc_id, rec["doc_version"], rec["file"])
        if src.exists():
            store_file(src, archive_path(self.paths, doc_id, rec["doc_version"], rec["file"]))
        rec.update(status="deleted", chunk_ids=[], chunk_count=0)
        self.ledger.event(doc_id, "deleted", "removed from the inbox; chunks deleted from the vector store; "
                          "file kept in the archive")
        self.log("deleted", doc=doc_id)

    def _finalise_collection(self, coll: Any, run_id: str) -> None:
        meta = dict(coll.metadata or {})
        meta.pop("hnsw:space", None)
        meta.update({
            "embed_model": self.settings.embed_model, "embed_model_version": self.embed_version,
            "dimension": meta.get("dimension") or self._dimension(coll),
            "index_id": uuid.uuid4().hex, "indexed_at": now(), "chunk_size": self.settings.chunk_size,
            "chunk_overlap": self.settings.chunk_overlap, "chunks": int(coll.count()),
            "collection_version": self.settings.collection, "ragops_run_id": run_id,
        })
        coll.modify(metadata=meta)

    @staticmethod
    def _dimension(coll: Any) -> int:
        row = coll.get(limit=1, include=["embeddings"])
        return len(row["embeddings"][0]) if row["ids"] else 0

    # ------------------------------------------------------------------ rollback and audit
    def rollback(self, family: str, to: str) -> dict[str, Any]:
        """Make an archived version of `family` the active one again (and archive the current one).

        `to` is a doc_id or a doc_version string. Chunks are flipped by metadata only when they
        are still in the vector store; otherwise the archived file is re-ingested.
        """
        members = self.ledger.family_members(family)
        target = next((m for m in members if to in (m["doc_id"], m["doc_version"]) and m["status"] == "archived"),
                      None)
        if target is None:
            raise KeyError(f"no archived version {to!r} in family {family!r}")
        run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-rollback"
        for m in members:
            if m["status"] == "active" and m["doc_id"] != target["doc_id"]:
                self._archive_document(m["doc_id"], superseded_by=target["doc_id"], run_id=run_id)
        method = "metadata flip"
        if self.count_by_doc(target["doc_id"]) == target["chunk_count"]:
            n = self._set_status(target["doc_id"], "active")
        else:
            file = archive_path(self.paths, target["doc_id"], target["doc_version"], target["file"])
            inp = DocInput(path=file, file=target["file"], sha256=target["file_sha"], size=file.stat().st_size,
                           origin=target["origin"], meta={"title": target["title"], "source": target["source"],
                                                           "date": target["date"], "doc_version": target["doc_version"],
                                                           "doc_family": family})
            ex = extract_document(inp, self.paths.state / "extract_cache")
            self._index_document(inp, ex, {"doc_embedding": target.get("doc_embedding"),
                                           "sketch": target.get("sketch")}, archived=False, run_id=run_id)
            n = self.count_by_doc(target["doc_id"])
            method = "re-ingested from the archive"
        target["status"] = "active"
        target.pop("superseded_by", None)
        self.ledger.event(target["doc_id"], "rollback", f"restored as the active version ({method})")
        coll = self._get_collection()
        if coll is not None:
            self._finalise_collection(coll, run_id)
        self.ledger.save()
        out = {"family": family, "restored": target["doc_id"], "version": target["doc_version"],
               "chunks_active": n, "method": method}
        self.log("rollback", **out)
        return out

    def audit(self) -> dict[str, Any]:
        """Compare Chroma with the ledger: orphans (chunks of a document the ledger does not hold),
        and ledger documents with missing chunks."""
        coll = self._get_collection()
        in_chroma: dict[str, int] = {}
        flags: dict[str, set[str]] = {}
        if coll is not None:
            offset = 0
            while True:
                page = coll.get(limit=500, offset=offset, include=["metadatas"])
                if not page["ids"]:
                    break
                for m in page["metadatas"]:
                    in_chroma[m["doc_id"]] = in_chroma.get(m["doc_id"], 0) + 1
                    flags.setdefault(m["doc_id"], set()).add(f"{m['status']}/superseded={m['superseded']}")
                offset += len(page["ids"])
        live = {r["doc_id"]: r for r in self.ledger.records()}
        orphans = {d: n for d, n in in_chroma.items() if d not in live}
        missing = {d: {"expected": r["chunk_count"], "found": in_chroma.get(d, 0)}
                   for d, r in live.items() if in_chroma.get(d, 0) != r["chunk_count"]}
        return {"chunks_by_doc": in_chroma, "status_flags": {d: sorted(v) for d, v in flags.items()},
                "orphan_chunks": orphans, "ledger_docs_with_missing_chunks": missing,
                "consistent": not orphans and not missing}

    # ------------------------------------------------------------------ reports
    def _write_reports(self, run_id: str, report: dict[str, Any], records: list[dict[str, Any]]) -> None:
        self.paths.reports.mkdir(parents=True, exist_ok=True)
        slim = [{k: v for k, v in r.items() if k not in ("doc_embedding", "sketch")} for r in records]
        summary = {"pass": sum(r["overall"] == "PASS" for r in records),
                   "fail": sum(r["overall"] == "FAIL" for r in records)}
        verification = {"run_id": run_id, "timestamp": report["timestamp"], "inbox": report["inbox"],
                        "summary": summary, "documents": slim}
        (self.paths.reports / f"verification-{run_id}.json").write_text(
            json.dumps(verification, indent=1), encoding="utf-8")
        (self.paths.reports / f"verification-{run_id}.md").write_text(
            verification_markdown(verification), encoding="utf-8")
        (self.paths.reports / f"ingest-{run_id}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        mirror = self.paths.results / "ingestion"
        try:
            mirror.mkdir(parents=True, exist_ok=True)
            for name in (f"verification-{run_id}.json", f"verification-{run_id}.md", f"ingest-{run_id}.json"):
                (mirror / name).write_text((self.paths.reports / name).read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass


def verification_markdown(v: dict[str, Any]) -> str:
    lines = [f"# Verification report {v['run_id']}", "",
             f"Inbox `{v['inbox']}` - {v['summary']['pass']} PASS, {v['summary']['fail']} FAIL", "",
             "| Document | quality | completeness | recency | uniqueness | Overall | Disposition |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in v["documents"]:
        c = d["checks"]
        lines.append(f"| {d['doc_name']} | " + " | ".join(c[n]["status"] for n in
                     ("quality", "completeness", "recency", "uniqueness"))
                     + f" | **{d['overall']}** | {d['disposition']} |")
    lines += ["", "## Reasons and recommended actions", ""]
    for d in v["documents"]:
        if d["overall"] == "FAIL" or d["advisories"] or d["supersedes"]:
            lines.append(f"### {d['doc_name']} ({d['overall']})")
            for r in d["failure_reasons"]:
                lines.append(f"- {r}")
            for a in d["advisories"]:
                lines.append(f"- advisory ({a['type']}, policy={a['policy']}): {a['matches'][0]}")
            if d["supersedes"]:
                lines.append(f"- supersedes: {', '.join(d['supersedes'])}")
            lines.append(f"- action: {d['recommended_action']}")
            lines.append("")
    return "\n".join(lines)
