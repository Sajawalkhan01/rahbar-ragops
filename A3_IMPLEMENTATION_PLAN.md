# A3 Implementation Plan and Progress Log

Working copy of the A2 ZIP: this directory (`Assignment-03-RAGOps`). Original ZIP and `../A2` untouched.
Tooling runs in WSL Ubuntu-22.04 (`~/rahbar-venv`, docker started with `sudo dockerd`, Ollama in `~/ollama`).
Project is symlinked in WSL as `~/ragops`.

## Decisions (and why)
| Decision | Why |
| --- | --- |
| New library package `ragops/` next to A2's `api/`, `indexer/`; A2 modules are imported, not copied | Extend, do not duplicate (rule 4/5) |
| Chroma over HTTP everywhere (docker locally, StatefulSet on k8s) | Same code path in dev and cluster; A2 `store.py` already does this |
| Full-suite generator = deterministic `extractive` provider plugged into A2's `LLMProvider` interface | Measured: CPU llama3.2:3b = ~1.5 tok/s, 110 s cold call. Suite x2 runs x baseline/candidate is infeasible. Real LLM is run on a small spot-check subset and reported separately |
| Faithfulness = deterministic lexical-support score (+ manual review sheet) | No judge LLM fast enough; documented as least-trusted metric |
| Ingestion state = JSON ledger on PVC + Chroma metadata (`doc_id`, `status`, `content_sha`) | Simple, inspectable, survives pod restarts |
| Tracing = JSONL (`traces/logs/`) + stdout, written from `answer_question` via a context-var recorder | Minimal change to A2 pipeline |

## Phases and status
| # | Phase | Status |
| --- | --- | --- |
| 0 | Inspect workspace, extract ZIP, analyse A2 | DONE |
| 1 | Part A ingestion: verification, quarantine, incremental, versioning, Batch B | DONE (verified, real Chroma + Ollama) |
| 2 | Part B eval: golden.jsonl, embedding/retrieval/generation eval, run-twice | DONE (member 2 confirms labels, hand review) |
| 3 | Part C experiment + release gate | DONE |
| 4 | Part D tracing, inspector, metrics, guardrail log, RCA | DONE except D5 write-up (member 2) |
| 5 | Part E coverage + drift | drift run DONE; coverage code DONE; live queries and new golden questions PENDING (member 2) |
| 6 | Part F Kubernetes (minikube) deploy, jobs, release, rollback | DONE with gaps listed in k8s/README.md |
| 7 | Part G report PDF + evidence | machinery DONE; text, screenshots PENDING (group) |
| 8 | README, FINAL_COMPLETION_REPORT, final test run | DONE (55 tests pass); final check after member 2 merges PENDING |

(Update the table as phases complete.)
