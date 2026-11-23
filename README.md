# RAHBAR + RAGOps (Assignment 03)

RAHBAR is the grounded question-answering pipeline from Assignment 02 (FAST-NUCES rules, fees and annual
reports). Assignment 03 adds a **RAGOps layer** to it, following Xu et al., *RAGOps: Operating and Managing
Retrieval-Augmented Generation Pipelines*: verified and incremental ingestion, three-level offline testing, a
release gate, per-query traces, query-coverage checking, and a Kubernetes release/rollback workflow.
The A2 code (`api/`, `indexer/`) is reused; the new code is `ragops/`, plus small, marked extensions in `api/app`.

| Part | What | Code |
| --- | --- | --- |
| A | verify, quarantine, incremental update, versions, Batch B | `ragops/ingestion/`, `eval/batch_b/`, `config/verification.yaml` |
| B | embedding / retrieval / end-to-end suite, golden set | `ragops/evaluation/`, `eval/golden.jsonl`, `config/evaluation.yaml` |
| C | experiment configs and the release gate | `experiments/`, `ragops/gate.py`, `config/release_thresholds.yaml` |
| D | traces, trace tool, metrics, guardrail log | `api/app/tracing.py`, `ragops/tracing/` |
| E | query coverage and drift | `ragops/evaluation/coverage.py`, `eval/live_queries/` |
| F | Kubernetes (minikube) | `k8s/` (start at `k8s/README.md`), `Dockerfile` |

Results are committed under `eval/results/` and `traces/`. Every number in the report comes from those files.

## Setup (WSL / Linux, Python 3.12)

```bash
python3 -m venv ~/rahbar-venv && ~/rahbar-venv/bin/pip install -r requirements-dev.txt
docker run -d --name chroma-dev -p 8000:8000 -v ~/chroma-data:/data -e IS_PERSISTENT=TRUE \
  -e PERSIST_DIRECTORY=/data chromadb/chroma:1.0.12            # the vector store
OLLAMA_HOST=0.0.0.0:11434 ~/ollama/bin/ollama serve &            # models: nomic-embed-text (embeddings)
cp .env.example .env                                              # placeholders only; no secrets are committed
```

`scripts/w.sh <cmd>` runs a command with the right environment (`scripts/dev-env.sh`: PYTHONPATH, Chroma and Ollama
addresses). Examples below use it: `bash scripts/w.sh python -m ...`.

## The commands, in execution order

**Unit tests (no model, no network):** `bash scripts/w.sh python -m pytest tests -q` (A3, 55 tests) and
`cd api && pytest -q`, `cd indexer && pytest -q` (A2, 98 + 77 tests).

**Part A: ingestion.** Stage the batches into inboxes, then ingest (verification runs inside).
```bash
cp -r corpus/raw data/inbox/batch_a                      # Batch A: the nine A2 documents (needs corpus/fetch.py)
cp -r eval/batch_b data/inbox/batch_b                    # Batch B: 18 files with planted problems
RAGOPS_ROLE=ingestor bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_a   # first ingestion
RAGOPS_ROLE=ingestor bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_a   # unchanged: 0 chunks embedded
RAGOPS_ROLE=ingestor bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_b   # Batch B
bash scripts/w.sh python -m ragops.ingestion quarantine list          # why each file was rejected
bash scripts/w.sh python -m ragops.ingestion audit                     # orphan / missing-chunk check
bash scripts/w.sh python -m ragops.ingestion status                    # ledger: documents, versions, status
RAGOPS_ROLE=ingestor bash scripts/w.sh python -m ragops.ingestion rollback --family fee-structure --to 2026-27
```
Reports: `eval/results/ingestion/verification-*.md|json`, `ingest-*.json`.

**Part B: the whole suite, one command** (writes `eval/results/suite-<label>-<timestamp>.json|md`, runs twice):
```bash
bash scripts/w.sh python -m ragops.evaluation.suite --label baseline --experiment experiments/baseline/baseline.yaml
```

**Part C: experiment and gate.**
```bash
CHROMA_COLLECTION=rahbar_c200 CHUNK_SIZE=200 CHUNK_OVERLAP=25 RAGOPS_ROLE=ingestor \
  bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_a            # build the candidate collection
bash scripts/w.sh python -m ragops.evaluation.suite --label candidate-chunk200 --experiment experiments/candidate/candidate-chunk200.yaml
bash scripts/w.sh python experiments/release_gate.py --baseline 'eval/results/suite-baseline-*.json' \
     --candidate 'eval/results/suite-candidate-chunk200-*.json'     # exit 0 = PASS, 1 = FAIL
```
Thresholds: `config/release_thresholds.yaml` (on Kubernetes: the `release-thresholds` ConfigMap).

**Part D: traces.** Every query appends a line to `traces/logs/`. Inspect one, or summarise the log:
```bash
bash scripts/w.sh python -m ragops.tracing.inspector <trace_id> --dir traces/logs        # context + prompt rebuild
bash scripts/w.sh python -m ragops.tracing.summary --dir traces/logs --since 24h --out traces/metrics/summary.json
```

**Part E: coverage.** `bash scripts/w.sh python -m ragops.evaluation.coverage --label before` (exit 1 below the
required share). Live queries: `eval/live_queries/live_queries.jsonl`.

**Part F: Kubernetes.** Everything is in `k8s/README.md` (start minikube, load the image, apply, run the Jobs,
release, reject, roll back, clean up).

**Evidence:** `bash scripts/capture.sh <id> "<command>"` saves the command and its unmodified output under
`reports/evidence/`.

## Layout

```
api/ indexer/ corpus/ ui/ docs/   Assignment 02 (reused; api/app has small, marked tracing extensions)
ragops/ingestion/                  Part A      ragops/evaluation/   Parts B, C, E      ragops/tracing/   Part D
config/                            verification.yaml, evaluation.yaml, release_thresholds.yaml
eval/                              golden.jsonl, batch_b/, noise_docs/, embedding_pairs.json, live_queries/, results/
experiments/                       baseline and candidate configs, release_gate.py
traces/                            logs/ (JSONL), metrics/
k8s/                               manifests (A2's older manifests are in k8s/base and k8s/overlays, not used by A3)
reports/                           assignment_03_report.pdf, evidence/
```

## Honest limitations

* The full suite uses a deterministic **extractive** generator (same `LLMProvider` interface, same validation).
  CPU-only `llama3.2:3b` ran at about 1.5 tokens/s here, so the suite cannot afford a language model.
  Faithfulness is a lexical measure and is high by construction for an extractive generator.
* Batch B is synthetic text written for this assignment, in the domain of the A2 corpus.
* See `FINAL_COMPLETION_REPORT.md` for what was verified and what still needs a person.
