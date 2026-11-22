"""Turns a question into an AskResponse. This is where the query pipeline lives (section 3.2).

    1. validate the question                      (schemas.AskRequest, before we get here)
    2. cache check, skipped for follow-ups        (cache.py, followup.py)
    3. embed the question                         (retriever.embed_query, same model as the indexer)
    4. retrieve top-k, superseded docs filtered   (retrieval/chroma.py)
    5. relevance floor: nothing relevant -> abstain WITHOUT calling the model
    6. augment + generate a schema-constrained answer     (prompt.py, providers/)
    7. validate: parse, check citations, retry once, then fall back   (validate.py)
    8. store the turn, and a cache entry if it is safe to cache

Each step is its own module so each can be unit-tested; this function only wires them.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .. import tracing
from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..providers.llm.usage import take_usage
from ..retrieval.base import Retriever
from ..retrieval.bm25 import exact_terms, tokenize
from ..routes import metrics
from ..schemas import Answer, AskResponse, Citation, Passage, RetrievedRef
from .cache import SemanticCache
from .prompt import _INJECTION, build_messages
from .followup import is_followup
from .turns import TurnStore
from .validate import generate_validated

log = logging.getLogger("rahbar.answer")

ABSTAIN_TEXT = (
    "The documents in this corpus do not cover that question, so I cannot answer it. "
    "Try rephrasing it, or ask about the academic rules, fees, grading, the student "
    "handbook or the annual reports."
)


def _is_relevant(question: str, passages: list[Passage], floor: float) -> bool:
    """Is anything retrieved relevant enough to answer from?

    Normally: the best passage's cosine similarity reaches the relevance floor. Exception: a
    question that names an exact term ("clause 1.21", "2.00", "10,000") is relevant to any passage
    that contains that term, however low its embedding score, because embeddings blur exactly
    these strings (the measured scores of such questions were 0.64 to 0.68 against a floor of
    0.70; see docs/PIPELINE.md).
    """
    terms = exact_terms(question)
    phrases = _phrases(tokenize(question))
    for p in passages:
        if p.score >= floor:
            return True
        words = tokenize(p.text)
        if terms and any(t in set(words) for t in terms):
            return True
        if phrases & _phrases(tokenize(p.text.replace("/", " "))):
            return True
    return False


PHRASE_WORDS = 3


def _phrases(words: list[str]) -> set[tuple[str, ...]]:
    """Runs of PHRASE_WORDS consecutive content words. A question such as "the Late Registration
    Fee" names its subject in words, not numbers; a passage that contains the same three
    content words in a row is about it even when a table's embedding score is low (0.67 here)."""
    return {tuple(words[i : i + PHRASE_WORDS]) for i in range(len(words) - PHRASE_WORDS + 1)}


def _refs(passages: list[Passage]) -> list[RetrievedRef]:
    return [
        RetrievedRef(chunk_id=p.chunk_id, source=p.source, section=p.section, page=p.page,
                     score=round(p.score, 4), doc_version=p.doc_version, superseded=p.superseded)
        for p in passages
    ]


def _cache_payload(response: AskResponse) -> dict[str, Any]:
    return response.model_dump(exclude={"request_id", "cached"})


def _doc_id(chunk_id: str) -> str:
    """Chunk ids are `<document slug>-<position>` (indexer/pipeline/chunk.py)."""
    return chunk_id.rsplit("-", 1)[0]


def _trace_retrieved(passages: list[Passage]) -> None:
    tracing.note(
        retrieved=[{"rank": n, "chunk_id": p.chunk_id, "doc_id": _doc_id(p.chunk_id), "source": p.source,
                    "section": p.section, "page": p.page, "doc_version": p.doc_version,
                    "superseded": p.superseded, "score": round(p.score, 4)}
                   for n, p in enumerate(passages, start=1)],
        context=[{"chunk_id": p.chunk_id, "text": p.text} for p in passages],
    )


def _trace_done(response: AskResponse, settings: Settings, provider: LLMProvider, **extra: Any) -> None:
    record = tracing.finish(
        request_id=response.request_id,
        model={"provider": provider.name, "llm_model": settings.llm_model,
               "temperature": settings.temperature, "top_k": settings.top_k,
               "relevance_floor": settings.relevance_floor, "hybrid": settings.hybrid,
               "filter_superseded": settings.filter_superseded},
        response={"answer": response.answer, "answered_from_context": response.answered_from_context,
                  "confidence": response.confidence, "cached": response.cached,
                  "invalid_citations_removed": response.invalid_citations_removed},
        citations=[c.model_dump() for c in response.citations],
        **extra,
    )
    if record is not None:
        for name, ms in record["latency_ms"].items():
            metrics.STAGE_SECONDS.labels(stage=name).observe(ms / 1000)
        for g in record["guardrails"]:
            if g["action"] == "injection_sentence_removed":
                metrics.INJECTIONS.labels(where="passage").inc()


def answer_question(
    question: str,
    retriever: Retriever,
    provider: LLMProvider,
    settings: Settings,
    cache: SemanticCache | None = None,
    turns: TurnStore | None = None,
    session_id: str | None = None,
) -> AskResponse:
    request_id = request_id_var.get()
    started = time.perf_counter()
    tracing.begin(question, embedding_model=settings.embed_model)
    info = getattr(retriever, "index_info", None)
    if info is not None:
        try:
            idx = info()
            tracing.note(collection=idx["collection"], index_id=idx["index_id"],
                         embedding_model=idx["embed_model"],
                         embedding_model_version=idx["embed_model_version"],
                         collection_version=idx["collection_version"])
        except Exception:   # a trace must never break an answer
            pass
    if _INJECTION.search(question):
        tracing.guardrail("question_injection_flagged",
                          reason="the question contains instruction-like text; it is fenced as data and "
                                 "the answer rules say not to follow it")
        metrics.INJECTIONS.labels(where="question").inc()

    # --- follow-up detection -------------------------------------------------------------
    previous = turns.last_question(session_id) if turns else None
    followup = is_followup(question, previous is not None)
    # A follow-up leans on the earlier turn, so retrieval sees both questions.
    search_text = f"{previous} {question}" if (followup and previous) else question
    if search_text != question:
        tracing.note(rewritten_query=search_text)

    # --- semantic cache (never for a follow-up) -----------------------------------------
    index_id = ""
    embedding: list[float] | None = None
    if cache is not None and settings.cache_enabled and not followup:
        try:
            with tracing.stage("embed_query"):
                embedding = retriever.embed_query(question)
            index_id = retriever.index_id()
        except Exception as exc:
            log.warning("cache skipped: could not embed the question", extra={"error": repr(exc)})
        if embedding is not None and index_id:
            with tracing.stage("cache_lookup"):
                hit = cache.lookup(index_id, embedding)
            if hit is not None:
                metrics.record_cache("hit")
                tracing.note(cache="hit", cache_similarity=round(hit.similarity, 4))
                response = AskResponse(**hit.payload, request_id=request_id, cached=True)
                _finish(turns, session_id, question, response, followup)
                _trace_done(response, settings, provider)
                log.info("answered", extra=_log_fields(
                    retriever, provider, settings, response, cache_result="hit",
                    similarity=round(hit.similarity, 4), followup=followup,
                    seconds=time.perf_counter() - started))
                return response
            metrics.record_cache("miss")
            tracing.note(cache="miss")
        else:
            metrics.record_cache("bypass")
    else:
        metrics.record_cache("bypass")

    # --- retrieval ----------------------------------------------------------------------
    t0 = time.perf_counter()
    with tracing.stage("retrieval"):
        passages = retriever.retrieve(search_text, k=settings.top_k)
    metrics.RETRIEVAL_SECONDS.observe(time.perf_counter() - t0)
    _trace_retrieved(passages)
    top_score = max((p.score for p in passages), default=0.0)
    metrics.TOP_SCORE.observe(max(top_score, 0.0))

    # --- honest abstention: nothing relevant retrieved -----------------------------------
    if not _is_relevant(question, passages, settings.relevance_floor):
        metrics.ABSTENTIONS.labels(reason="floor").inc()
        tracing.guardrail("abstain_below_relevance_floor", top_score=round(top_score, 4),
                          floor=settings.relevance_floor,
                          reason="no retrieved passage reached the floor and none contains the question's exact terms")
        response = AskResponse(
            request_id=request_id, answer=ABSTAIN_TEXT, citations=[],
            answered_from_context=False, confidence="high", retrieved=_refs(passages),
            provider=provider.name,
        )
        _finish(turns, session_id, question, response, followup)
        _trace_done(response, settings, provider, abstain_reason="below relevance floor",
                    top_score=round(top_score, 4))
        log.info("answered", extra=_log_fields(
            retriever, provider, settings, response, cache_result="miss" if embedding else "bypass",
            followup=followup, abstain_reason="below relevance floor",
            floor=settings.relevance_floor, top_score=round(top_score, 4),
            seconds=time.perf_counter() - started))
        return response

    # --- generation, validation, citation check -----------------------------------------
    prompt_messages = build_messages(question, passages)   # the text the provider renders: hash + guardrails
    tracing.note(prompt_hash=tracing.prompt_hash(prompt_messages))
    t0 = time.perf_counter()
    with tracing.stage("generation"):
        generation = generate_validated(provider, question, passages)
    metrics.GENERATION_SECONDS.labels(provider=provider.name).observe(time.perf_counter() - t0)
    usage = take_usage()
    metrics.TOKENS.labels(direction="input").inc(usage.input_tokens)
    metrics.TOKENS.labels(direction="output").inc(usage.output_tokens)
    if generation.citations_removed:
        metrics.CITATIONS_REMOVED.inc(generation.citations_removed)
        tracing.guardrail("citations_removed", count=generation.citations_removed,
                          reason="the model cited a passage that was not in the retrieved evidence")
    if generation.fell_back:
        metrics.FALLBACKS.inc()
        tracing.guardrail("fallback_answer", reason=generation.error or "model output failed validation twice")

    answer: Answer = generation.answer
    citations: list[Citation] = generation.citations or []
    if not answer.answered_from_context:
        if not generation.fell_back:
            metrics.ABSTENTIONS.labels(reason="model").inc()
        citations = []

    response = AskResponse(
        request_id=request_id,
        answer=answer.answer.strip() or ABSTAIN_TEXT,
        citations=citations,
        answered_from_context=answer.answered_from_context,
        confidence=answer.confidence,
        retrieved=_refs(passages),
        provider=provider.name,
        invalid_citations_removed=generation.citations_removed,
    )

    # --- cache only what is safe to serve to everyone ------------------------------------
    cacheable = (
        cache is not None and embedding is not None and index_id
        and not followup
        and response.answered_from_context
        and not generation.fell_back
        and bool(citations)
    )
    if cacheable:
        assert cache is not None and embedding is not None
        cache.store(index_id, question, embedding, _cache_payload(response))

    _finish(turns, session_id, question, response, followup)
    _trace_done(response, settings, provider, attempts=generation.attempts, top_score=round(top_score, 4))
    log.info("answered", extra=_log_fields(
        retriever, provider, settings, response,
        cache_result="miss" if embedding is not None else "bypass", followup=followup,
        attempts=generation.attempts, fell_back=generation.fell_back,
        citations_removed=generation.citations_removed, cached_now=bool(cacheable),
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        top_score=round(top_score, 4), seconds=time.perf_counter() - started))
    return response


def _finish(
    turns: TurnStore | None, session_id: str | None, question: str, response: AskResponse,
    followup: bool,
) -> None:
    if turns is not None:
        turns.add(session_id, question, response.answered_from_context, response.cached)


def _log_fields(
    retriever: Retriever, provider: LLMProvider, settings: Settings, response: AskResponse,
    **extra: Any,
) -> dict[str, Any]:
    """The one line per request that makes a wrong answer diagnosable (section 4.8).
    Never includes the question text's secrets or any credential: only ids and numbers."""
    fields: dict[str, Any] = {
        "retriever": retriever.name,
        "provider": provider.name,
        "top_k": settings.top_k,
        "chunk_ids": [r.chunk_id for r in response.retrieved],
        "scores": [r.score for r in response.retrieved],
        "abstained": not response.answered_from_context,
        "answered_from_context": response.answered_from_context,
        "n_citations": len(response.citations),
    }
    if "seconds" in extra:
        extra["seconds"] = round(extra["seconds"], 3)
    fields.update(extra)
    return fields
