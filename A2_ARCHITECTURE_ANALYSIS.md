# A2 architecture analysis (RAHBAR)

What the Assignment 02 system is, which parts Assignment 03 reuses unchanged, and which parts it extends.
Source: the A2 ZIP, read file by file (paths relative to this repository).

## 1. System in one paragraph

RAHBAR answers questions about FAST-NUCES rules, fees and annual reports from a nine-document corpus
(281 pages). An **indexer Job** extracts, cleans, chunks and embeds the documents and is the only writer to
**Chroma**; an **API** embeds the question, runs hybrid retrieval (dense + BM25 + exact-term fusion) with a
version filter, applies a relevance floor, asks an LLM for a schema-constrained JSON answer, validates the
answer and its citations, and caches safe answers in **Redis**. It runs on Kubernetes (minikube).

## 2. Components and where they live

| Stage | A2 file | What it does |
| --- | --- | --- |
| Corpus fetch | `corpus/fetch.py`, `corpus/sources.yaml`, `corpus/raw/_index.json` | downloads public documents; manifest has `doc_version` and `superseded` per file |
| Extraction | `indexer/pipeline/extract.py` | PDF text in reading order (column gutters), tables as `a \| b` rows, OCR (Tesseract) for pages with no text layer, HTML/Markdown parsers |
| Cleaning | `indexer/pipeline/clean.py` | NFKC, control characters, dot leaders, hyphenation, repeated headers and footers |
| Chunking | `indexer/pipeline/chunk.py` | structure-aware, 400 words / 50 overlap, heading carried as `section`, stable ids `<doc-slug>-<pos>` |
| Embedding | `indexer/pipeline/embed.py` | Ollama `nomic-embed-text` (768-d), `search_document:` prefix; pinned by `EMBED_MODEL` |
| Store | `indexer/pipeline/store.py` | upsert, delete stale ids, collection metadata (`embed_model`, `dimension`, `index_id`, ...) |
| Retrieval | `api/app/retrieval/chroma.py`, `bm25.py`, `versions.py` | dense + BM25 + exact-term ranking, reciprocal rank fusion, `superseded == False` filter unless the question asks for an older version |
| Embedder (query) | `api/app/retrieval/embedder.py` | `search_query:` prefix, same model |
| Pin check | `api/app/retrieval/pin.py`, `readiness.py` | the API refuses readiness if its embedding model differs from the index |
| Query pipeline | `api/app/services/answer.py` | cache, retrieve, relevance floor (abstain without calling the model), generate, validate, cache store |
| Prompt + guardrail | `api/app/services/prompt.py` | evidence fenced in `<evidence>`, `neutralise_injection()` removes instruction-like sentences from passages, answer rules |
| Validation | `api/app/services/validate.py`, `citations.py` | schema check, one retry, citation must match a retrieved passage, fallback text |
| Providers | `api/app/providers/llm/{stub,ollama,hosted}.py` | `LLMProvider.generate(question, passages) -> Answer` |
| Cache | `api/app/services/cache.py` | Redis semantic cache keyed by `index_id`, threshold 0.94 |
| API | `api/app/main.py`, `routes/{ask,health,metrics}.py` | FastAPI; `/api/ask`, `/healthz`, `/readyz`, Prometheus `/metrics` |
| Logs | `api/app/logjson.py` | JSON logs to stdout with request id |
| Manifests | `k8s/base/*`, `k8s/overlays/*` | namespace `rahbar`; api Deployment (3 replicas, `maxUnavailable: 0`), chroma StatefulSet, redis, indexer Job, reindex CronJob, HPA, Ingress, NetworkPolicies |
| Evaluation | `eval/run_eval.py`, `eval/golden.yaml` | 21-question golden set, recall@k, citation validity, abstention; CI gate against `eval/baseline.json` |
| Tests | `api/tests`, `indexer/tests`, `tests/test_eval.py` | 98 + 77 tests, all with fakes (no model, no network) |

Measured by A2 and recorded in `docs/PIPELINE.md`: chunk 400/50 recall@3 = recall@5 = 1.0 on its 18 answerable
questions; relevance floor 0.70; cache threshold 0.94; CPU-only Ollama `llama3.2:3b` is too slow to evaluate with.

## 3. How A2 runs

`make cluster` (minikube + Calico), `make images`, `make apply` (kustomize dev overlay), the indexer Job fetches
and indexes the corpus (OCR of 32 scanned pages takes 15-30 minutes), the API serves through an Ingress.

## 4. What A2 already gave Assignment 03 (reused unchanged)

* the whole extraction, cleaning, chunking, embedding and storage code (imported as `pipeline.*`);
* the retriever, version filter, relevance floor, prompt, injection filter and citation validation (imported as `app.*`);
* A2's scoring functions `_matches` and `citation_counts` (`eval/run_eval.py`), used by the new evaluation suite;
* the Chroma StatefulSet pattern, probes, security contexts and rolling-update settings (copied into `k8s/`);
* the `LLMProvider` interface, which the new `extractive` provider plugs into.

## 5. What A2 lacked (and A3 adds)

| Gap in A2 | A3 addition |
| --- | --- |
| Every run re-embeds the whole corpus; no document-level change detection | `ragops/ingestion/incremental.py`: hash-based ledger, chunk-text-hash reuse, per-document replace |
| No verification: a corrupt, empty, duplicate or stale file is indexed as is | `ragops/ingestion/verification.py` with four checks, quarantine, report per run |
| `superseded` is set once in a manifest; no version lifecycle | archive on supersession, metadata flip, rollback command, orphan audit |
| One 21-question golden set; no embedding or noise tests | `eval/golden.jsonl` (34 questions), embedding pairs, noise tests, run-twice suite |
| No experiment/release process | `experiments/`, `ragops/gate.py`, ConfigMap thresholds, candidate Deployment |
| JSON logs, no per-query record | `api/app/tracing.py` + trace inspector + log summary + guardrail actions in the trace |
| Jobs not tied to results/traces volumes | PVCs for data lake, results and traces |

## 6. Constraints that shaped the design

* **CPU-only LLM.** Ollama `llama3.2:3b` measured at about 1.5 tokens/s on this laptop (one cold 39-token reply took
  110 s). A full suite run twice, for a baseline and a candidate, is impractical, so the suite runs A2's real
  pipeline with a deterministic `extractive` provider (same interface and validation) and a small real-LLM spot check.
* **5.9 GB RAM** in WSL for Docker, minikube, Ollama and Chroma together.
* **Single writer.** A2 already says the indexer is the only writer (ADR 0001); A3 enforces it in code (role + lock).
* **A2 limits kept:** BM25 is rebuilt per replica from Chroma (30 s snapshot refresh), English-only tokenizer.
