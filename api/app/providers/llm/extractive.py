"""A deterministic, model-free provider for the evaluation suite (Assignment 03).

Why it exists: a CPU-only laptop runs the 3B Ollama model at about 1.5 tokens/s (measured: 110 s for
a 39-token reply), so the full suite, run twice for the baseline and again for each candidate, cannot
use a language model. This provider plugs into the SAME LLMProvider interface and the SAME validation
(services/validate.py): it answers with the best-matching sentences of the retrieved passages and
cites the passages they came from, or declines when no sentence overlaps the question enough.

What it measures and what it cannot: retrieval quality, citation handling, abstention and latency
of everything except the language model. Its answers are copied from the context, so faithfulness is
high by construction. The suite therefore reports it as the least informative generation metric,
and a small live-LLM run (eval/results/llm_spotcheck_*.json) is reported separately.
Retrieved text goes through the same injection filter as the real prompt.
"""

from __future__ import annotations

import os
import re

from ...config import Settings
from ...retrieval.bm25 import exact_terms, tokenize
from ...schemas import Answer, Citation, Passage
from ...services.prompt import _FENCE, REMOVED_MARKER, neutralise_injection
from .usage import record_usage

MAX_SENTENCES = 2      # best-matching sentences used as answer seeds
CONTINUATION = 2       # lines after a seed that are kept with it: a table row or list item holds the value
MAX_WORDS = 90


_ABBREVIATIONS = ("rs.", "no.", "dr.", "mr.", "mrs.", "prof.", "e.g.", "i.e.", "etc.", "vs.", "w.e.f.", "approx.", "sr.")


def _split_line(line: str) -> list[str]:
    """Split a line at sentence ends, but not after an abbreviation such as 'Rs.' or 'e.g.'."""
    pieces = re.split(r"(?<=[.!?])\s+", line)
    out: list[str] = []
    for piece in pieces:
        if out and out[-1].lower().endswith(_ABBREVIATIONS):
            out[-1] = f"{out[-1]} {piece}"
        else:
            out.append(piece)
    return out


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.extend(s.strip() for s in _split_line(line) if s.strip())
    return out


def _join(best: list) -> str:  # type: ignore[type-arg]
    """Each seed sentence plus the lines that follow it, capped at MAX_WORDS."""
    parts: list[str] = []
    for _, _, _, sentence, _, follow in best:
        parts.append(" ".join([sentence, *follow]))
    words = " ".join(parts).split()
    return " ".join(words[:MAX_WORDS])


class ExtractiveProvider:
    name = "extractive"

    def __init__(self, settings: Settings | None = None) -> None:
        self.min_overlap = float(os.environ.get("EXTRACTIVE_MIN_OVERLAP", "0.34"))

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        record_usage(sum(len(p.text.split()) for p in passages) + len(question.split()), 30)
        q_words = set(tokenize(_FENCE.sub(" ", question)))
        q_terms = set(exact_terms(question))
        scored: list[tuple[float, int, int, str, Passage, list[str]]] = []
        for rank, p in enumerate(passages):
            clean = neutralise_injection(_FENCE.sub(" ", p.text), p.chunk_id)
            heading = set(tokenize(p.section))
            lines = [s for s in _sentences(clean)]
            for n, sentence in enumerate(lines):
                if REMOVED_MARKER in sentence:
                    continue
                words = set(tokenize(sentence)) | heading
                if not q_words:
                    continue
                overlap = len(q_words & words) / len(q_words)
                if q_terms & words:
                    overlap += 0.25
                follow = [t for t in lines[n + 1 : n + 1 + CONTINUATION] if REMOVED_MARKER not in t]
                scored.append((overlap, -rank, -n, sentence, p, follow))
        scored.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
        best = [t for t in scored if t[0] >= self.min_overlap][:MAX_SENTENCES]
        if not best:
            return Answer(reasoning="extractive: no sentence overlaps the question enough",
                          answer="The documents do not cover that question.", citations=[],
                          answered_from_context=False, confidence="low")
        citations: list[Citation] = []
        for _, _, _, _, p, _ in best:
            c = Citation(source=p.source, section=p.section, page=p.page)
            if c not in citations:
                citations.append(c)
        top = best[0][0]
        return Answer(reasoning=f"extractive: top sentence overlap {top:.2f}",
                      answer=_join(best), citations=citations,
                      answered_from_context=True,
                      confidence="high" if top >= 0.8 else "medium" if top >= 0.5 else "low")
