"""A1: the verification stage. Runs after extraction and before chunking.

Four checks per document, each with PASS/FAIL and a reason (assignment A1):
  quality       empty, too short, garbled, failed extraction
  completeness  source, title, date or version present; page count; text not truncated
  recency       a newer version of the same family exists (or this one is a stale re-submission)
  uniqueness    exact duplicate (file hash, text hash) and near-duplicate (embedding similarity)
An advisory scan (not one of the four) flags instruction-like text. All thresholds live in
config/verification.yaml.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .documents import DocInput
from .extraction import Extraction

EmbedFn = Callable[[list[str]], list[list[float]]]
CHECKS = ("quality", "completeness", "recency", "uniqueness")


def _result(ok: bool, reason: str, details: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    return {"status": "PASS" if ok else "FAIL", "reason": reason, "details": details or [], **extra}


# ----------------------------------------------------------------------------- helpers
def normalise(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def text_sha256(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def version_key(version: Any) -> tuple[int, ...]:
    """'2026-06' -> (2026, 6); '2027-28' -> (2027, 28); 'v2.1' -> (2, 1); unknown -> ()."""
    return tuple(int(n) for n in re.findall(r"\d+", str(version or "")))


def sketch(text: str, shingle: int = 5, k: int = 128) -> list[int]:
    """Bottom-k MinHash-style sketch of word shingles: the k smallest hashes. Two sketches give
    an estimate of the Jaccard similarity of the full shingle sets without storing the text."""
    words = normalise(text).split()
    grams = {" ".join(words[i : i + shingle]) for i in range(max(1, len(words) - shingle + 1))}
    hashes = sorted(int(hashlib.md5(g.encode()).hexdigest()[:12], 16) for g in grams)
    return hashes[:k]


def jaccard_from_sketches(a: list[int], b: list[int]) -> float:
    if not a or not b:
        return 0.0
    k = min(len(a), len(b), 128)
    union = sorted(set(a) | set(b))[:k]
    sa, sb = set(a), set(b)
    both = sum(1 for h in union if h in sa and h in sb)
    return both / len(union) if union else 0.0


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def doc_embedding(text: str, embed: EmbedFn, windows: int, window_words: int) -> list[float]:
    """Mean of the embeddings of `windows` evenly spaced slices of the document."""
    words = text.split()
    if len(words) <= window_words:
        parts = [" ".join(words)]
    else:
        starts = [round(i * (len(words) - window_words) / max(1, windows - 1)) for i in range(windows)]
        parts = [" ".join(words[s : s + window_words]) for s in dict.fromkeys(starts)]
    vectors = embed(parts)
    return [sum(col) / len(vectors) for col in zip(*vectors)]


# ----------------------------------------------------------------------------- checks
def check_quality(ex: Extraction, cfg: dict[str, Any]) -> dict[str, Any]:
    q = cfg["quality"]
    if ex.error or ex.document is None:
        return _result(False, f"extraction failed: {ex.error or 'no document produced'}",
                       category="corrupt")
    text = ex.text
    stripped = text.strip()
    if not stripped:
        return _result(False, "document is empty: extraction produced no text", category="empty")
    chars, words = len(stripped), len(stripped.split())
    problems: list[str] = []
    if chars < q["min_chars"] or words < q["min_words"]:
        problems.append(f"insufficient content: {chars} characters, {words} words "
                        f"(minimum {q['min_chars']} / {q['min_words']})")
    nonspace = [c for c in stripped if not c.isspace()]
    bad = sum(1 for c in nonspace if c == "�" or (ord(c) < 32 and c not in "\t\n\r"))
    if nonspace and bad / len(nonspace) > q["max_replacement_char_share"]:
        problems.append(f"garbled: {bad / len(nonspace):.1%} replacement/control characters")
    alnum = sum(c.isalnum() for c in nonspace)
    if nonspace and alnum / len(nonspace) < q["min_alnum_share"]:
        problems.append(f"garbled: only {alnum / len(nonspace):.0%} alphanumeric characters "
                        f"(minimum {q['min_alnum_share']:.0%})")
    tokens = re.findall(r"\S+", stripped)
    if tokens:
        implausible = sum(1 for t in tokens if _implausible(t))
        share = implausible / len(tokens)
        if share > q["max_implausible_token_share"]:
            problems.append(f"garbled: {share:.0%} of tokens are not word-like "
                            f"(maximum {q['max_implausible_token_share']:.0%})")
    if problems:
        category = "garbled" if any(p.startswith("garbled") for p in problems) else "insufficient"
        return _result(False, problems[0], problems, category=category)
    return _result(True, f"{chars} characters, {words} words, readable",
                   metrics={"chars": chars, "words": words})


def _implausible(token: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", token)
    if len(letters) >= 6 and not re.search(r"[aeiouyAEIOUY]", letters):
        return True
    symbols = sum(1 for c in token if not c.isalnum())
    return len(token) >= 4 and symbols / len(token) > 0.6 and not re.fullmatch(r"[|\-_=.]+", token)


def check_completeness(inp: DocInput, ex: Extraction, cfg: dict[str, Any]) -> dict[str, Any]:
    c = cfg["completeness"]
    missing = [k for k in c["required_metadata"] if not inp.meta.get(k)]
    if c.get("require_date_or_version") and not (inp.meta.get("date") or inp.meta.get("doc_version")):
        missing.append("date_or_version")
    problems: list[str] = []
    if missing:
        problems.append(f"missing metadata: {', '.join(missing)}")
    category = "missing_metadata" if missing else ""
    if ex.document is not None and ex.ok:
        pages = len(ex.document.pages)
        if inp.path.suffix.lower() == ".pdf":
            if pages < 1:
                problems.append("page count unavailable: no pages extracted")
            declared = inp.meta.get("pages")
            tol = c["truncation"].get("declared_pages_tolerance", 0)
            if declared and abs(int(declared) - pages) > tol:
                problems.append(f"truncated: metadata declares {declared} pages, extracted {pages}")
                category = "truncated"
        elif c["truncation"].get("check_text_end") and inp.path.suffix.lower() in c["truncation"].get(
                "text_end_applies_to", [".md", ".txt", ".html", ".htm"]):
            reason = _truncated_end(ex.text, c["truncation"])
            if reason:
                problems.append(f"truncated: {reason}")
                category = "truncated"
    if problems:
        return _result(False, "; ".join(problems), problems, category=category or "incomplete")
    return _result(True, "required metadata present, text complete",
                   page_count=len(ex.document.pages) if ex.document else None)


def _truncated_end(text: str, t: dict[str, Any]) -> str:
    body = text.rstrip()
    if not body:
        return ""
    last_line = body.splitlines()[-1].strip()
    if len(last_line.split()) < t["min_end_words"] or last_line.startswith("#"):
        return ""
    if last_line[-1] in "".join(t["ends_ok"]) or last_line[-1].isdigit():
        return ""
    return f"text ends mid-sentence: ...{last_line[-50:]!r}"


def check_recency(inp: DocInput, ledger_docs: list[dict[str, Any]], batch: list[DocInput],
                  cfg: dict[str, Any]) -> dict[str, Any]:
    """Compare against the other versions of the same family (ledger + this batch)."""
    mine = version_key(inp.meta.get("doc_version") or inp.meta.get("date"))
    others: list[tuple[str, tuple[int, ...]]] = []
    for d in ledger_docs:
        if d["family"] == inp.family and d["doc_id"] != inp.doc_id and d["status"] != "deleted":
            others.append((d["doc_id"], version_key(d.get("doc_version") or d.get("date"))))
    for o in batch:
        if o.family == inp.family and o.doc_id != inp.doc_id:
            others.append((o.doc_id, version_key(o.meta.get("doc_version") or o.meta.get("date"))))
    if not others or not mine:
        return _result(True, "no other version of this document family", supersedes=[], superseded_by=[])
    newer = [(i, k) for i, k in others if k > mine]
    older = [(i, k) for i, k in others if k and k < mine]
    if newer and not inp.declared_superseded and cfg["recency"]["reject_stale_resubmission"]:
        names = ", ".join(f"{i} ({'.'.join(map(str, k))})" for i, k in newer)
        return _result(False, f"stale: a newer version exists ({names}) and this document is not "
                       "declared superseded", category="stale",
                       superseded_by=[i for i, _ in newer], supersedes=[])
    if newer:
        return _result(True, "older version declared superseded; it will be indexed as archived",
                       superseded_by=[i for i, _ in newer], supersedes=[])
    if older:
        return _result(True, "newer version of " + ", ".join(i for i, _ in older)
                       + "; the older version will be archived",
                       supersedes=[i for i, _ in older], superseded_by=[])
    return _result(True, "same version as the other document of its family",
                   supersedes=[], superseded_by=[])


@dataclass
class Known:
    """What the uniqueness check compares against: the index plus documents accepted in this run."""

    by_sha: dict[str, str] = field(default_factory=dict)         # file sha -> doc_id
    by_text_sha: dict[str, str] = field(default_factory=dict)    # normalised-text sha -> doc_id
    embeddings: dict[str, list[float]] = field(default_factory=dict)
    sketches: dict[str, list[int]] = field(default_factory=dict)
    families: dict[str, str] = field(default_factory=dict)       # doc_id -> family

    def add(self, doc_id: str, family: str, sha: str, tsha: str, emb: list[float] | None,
            sk: list[int] | None) -> None:
        self.by_sha[sha] = doc_id
        self.by_text_sha[tsha] = doc_id
        self.families[doc_id] = family
        if emb is not None:
            self.embeddings[doc_id] = emb
        if sk is not None:
            self.sketches[doc_id] = sk


def check_uniqueness(inp: DocInput, ex: Extraction, known: Known, embed: EmbedFn | None,
                     cfg: dict[str, Any]) -> tuple[dict[str, Any], list[float] | None, list[int] | None]:
    u = cfg["uniqueness"]
    if u.get("exact_hash") and (other := known.by_sha.get(inp.sha256)) and other != inp.doc_id:
        return (_result(False, f"exact duplicate of {other} (same file SHA-256)",
                        category="duplicate_exact", duplicate_of=other), None, None)
    tsha = text_sha256(ex.text) if ex.ok else ""
    if u.get("text_hash") and tsha and (other := known.by_text_sha.get(tsha)) and other != inp.doc_id:
        return (_result(False, f"exact duplicate of {other} (identical normalised text)",
                        category="duplicate_exact", duplicate_of=other), None, None)
    emb: list[float] | None = None
    sk: list[int] | None = None
    nd = u["near_duplicate"]
    if ex.ok and nd["enabled"] and embed is not None:
        emb = doc_embedding(ex.text, embed, nd["windows"], nd["window_words"])
        sk = sketch(ex.text, nd["shingle_words"])
        best: tuple[float, float, str] = (0.0, 0.0, "")
        for other_id, other_emb in known.embeddings.items():
            if other_id == inp.doc_id or known.families.get(other_id) == inp.family:
                continue   # another version of the same family is a version, not a duplicate
            sim = cosine(emb, other_emb)
            lex = jaccard_from_sketches(sk, known.sketches.get(other_id, []))
            if sim >= nd["embedding_threshold"] and (
                    not nd["require_lexical_confirmation"] or lex >= nd["lexical_threshold"]):
                if sim > best[0]:
                    best = (sim, lex, other_id)
        if best[2]:
            return (_result(False, f"near-duplicate of {best[2]} (embedding cosine {best[0]:.3f}, "
                            f"shingle overlap {best[1]:.2f})", category="duplicate_near",
                            duplicate_of=best[2], similarity=round(best[0], 4),
                            lexical=round(best[1], 3)), emb, sk)
    return _result(True, "unique: no exact or near duplicate"), emb, sk


# ----------------------------------------------------------------------------- advisory
def injection_advisory(text: str) -> list[str]:
    """A2's query-time rail (app.services.prompt) reused as an ingest-time scan."""
    from app.services.prompt import _INJECTION

    hits = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if _INJECTION.search(sentence):
            hits.append(sentence.strip()[:160])
    return hits[:5]


# ----------------------------------------------------------------------------- orchestration
ACTIONS = {
    "corrupt": "Re-export or re-download the file; if it opens elsewhere, re-run extraction/OCR, then resubmit.",
    "empty": "The file has no extractable text (scan without OCR?). Resubmit a text version.",
    "insufficient": "The document has too little content to be useful. Resubmit the full document.",
    "garbled": "Text is unreadable (bad encoding or OCR). Fix the source encoding or re-run OCR, then resubmit.",
    "missing_metadata": "Add the missing metadata (title, source, date or version) and resubmit.",
    "truncated": "Obtain the complete file (the upload was cut off) and resubmit.",
    "incomplete": "Complete the document and its metadata, then resubmit.",
    "stale": "Do not index. Submit the current version, or set `superseded: true` if the old one must stay searchable.",
    "duplicate_exact": "Discard: the original is already indexed. No action needed.",
    "duplicate_near": "Review against the original. If it is a new version set doc_family and doc_version; otherwise discard.",
    "injection": "Remove the instruction-like text from the source and resubmit.",
}


def verify_batch(docs: list[DocInput], extractions: dict[str, Extraction],
                 ledger_docs: list[dict[str, Any]], known: Known, embed: EmbedFn | None,
                 cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the four checks for every document in canonical order; return one record per document.

    Canonical order is (file name length, name): for a group of duplicates the shortest, most
    'original' name is kept and the copies are the ones rejected.
    """
    records: list[dict[str, Any]] = []
    mandatory = set(cfg.get("mandatory_checks", CHECKS))
    # Only documents that could be indexed (readable, with a version or date) count as "another
    # version" for the recency check: a corrupt newer file must not make a good older one stale.
    pool = [d for d in docs if extractions[d.file].ok and (d.meta.get("doc_version") or d.meta.get("date"))]
    for inp in sorted(docs, key=lambda d: (len(d.file), d.file)):
        ex = extractions[inp.file]
        started = time.perf_counter()
        quality = check_quality(ex, cfg)
        completeness = check_completeness(inp, ex, cfg)
        recency = check_recency(inp, ledger_docs, pool, cfg)
        emb = sk = None
        if quality["status"] == "PASS":
            uniqueness, emb, sk = check_uniqueness(inp, ex, known, embed, cfg)
        else:
            uniqueness = _result(True, "skipped: the document failed the quality check first")
            uniqueness["skipped"] = True
        checks = {"quality": quality, "completeness": completeness, "recency": recency,
                  "uniqueness": uniqueness}
        failed = [n for n in CHECKS if checks[n]["status"] == "FAIL" and n in mandatory]
        overall = "FAIL" if failed else "PASS"
        categories = [checks[n].get("category", n) for n in failed]
        reasons = [f"{n}: {checks[n]['reason']}" for n in failed]
        advisories: list[dict[str, Any]] = []
        if ex.ok and (hits := injection_advisory(ex.text)):
            policy = cfg["advisories"]["injection_policy"]
            advisories.append({"type": "prompt_injection", "policy": policy, "matches": hits,
                               "note": "instruction-like text found; the query-time rail "
                                       "(app.services.prompt.neutralise_injection) removes it "
                                       "before generation"})
            if policy == "quarantine":
                overall = "FAIL"
                categories.append("injection")
                reasons.append("advisory: instruction-like text: " + hits[0])
        if overall == "PASS":
            disposition = "index_archived" if recency.get("superseded_by") else "index"
            known.add(inp.doc_id, inp.family, inp.sha256, text_sha256(ex.text), emb, sk)
        else:
            disposition = "quarantine"
        records.append({
            "doc_id": inp.doc_id,
            "doc_name": inp.file,
            "title": inp.meta.get("title"),
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "file_sha256": inp.sha256,
            "checks": checks,
            "overall": overall,
            "failure_reasons": reasons,
            "categories": categories,
            "recommended_action": " ".join(dict.fromkeys(ACTIONS.get(c, "Inspect manually.")
                                                         for c in categories))
                                  or ("Index; the older version will be archived."
                                      if recency.get("supersedes") else "Index."),
            "disposition": disposition,
            "advisories": advisories,
            "supersedes": recency.get("supersedes", []),
            "superseded_by": recency.get("superseded_by", []),
            "doc_embedding": emb,
            "sketch": sk,
            "seconds": round(time.perf_counter() - started, 3),
        })
    return records
