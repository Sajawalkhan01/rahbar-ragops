# A3 requirements checklist

Every requirement of the official brief (`Assignment_03.pdf`) mapped to its implementation, how it is checked, where the
evidence is, and its status. Status words: **PASS** = implemented and verified by a run; **PENDING** = not done yet or
needs a person or an environment I do not have; **FAIL** = tried, did not verify.
Last updated: see git log. Rows owned by the second group member are marked (member 2).

## Part A: data management

| Req | Implementation | Check | Evidence | Status |
| --- | --- | --- | --- | --- |
| A1 verification after ingestion, before chunking; four checks with reason per document | `ragops/ingestion/verification.py`, `config/verification.yaml` | `tests/test_ingestion.py` (checks), Batch A and B runs | `eval/results/ingestion/verification-*.md/.json` | PASS |
| A1 failed documents moved to quarantine, not indexed; report file per run | `ragops/ingestion/state.py` (`Quarantine`), `incremental.py` | tests: moved, logged, never indexed, skipped on resubmission | `data/quarantine/quarantine_log.jsonl`, verification report | PASS |
| A2 unchanged re-run embeds zero chunks (counts shown) | `ragops/ingestion/incremental.py` (ledger, `_intact`) | `test_unchanged_rerun_embeds_zero_chunks`; real run: second run `chunks_embedded: 0` | `eval/results/ingestion/ingest-*batchA-second.json` | PASS |
| A2 changed document replaces only its own chunks | `_index_document` (chunk text-hash reuse, stale delete) | `test_changed_document_replaces_only_its_own_chunks` | ingest report `changed` / `chunks_embedded` | PASS (unit); real-cluster demo PENDING |
| A2 deleted document leaves no orphans (count by document id) | `_delete_document`, `count_by_doc`, `audit` | `test_deleted_document_leaves_no_orphan_chunks` | report `orphan_chunk_counts_after_delete` | PASS (unit) |
| A2 superseded version archived, excluded by metadata, restorable (rollback) | `_archive_document`, `rollback` | `test_newer_version_archives...`, `test_rollback_reingests...` | ledger history, `archive/` | PASS (unit) |
| Batch B >= 10 documents with the planted problems | `eval/batch_b/` (18 files), `build_batch_b.py`, `README.md` | `test_batch_b_dispositions` | Batch B verification report | PASS |
| Run both batches through A1 and A2 | `python -m ragops.ingestion run` | Batch A run on real Chroma + Ollama | reports | Batch A PASS; Batch B see below |

## Part B: offline testing

| Req | Implementation | Check | Evidence | Status |
| --- | --- | --- | --- | --- |
| Golden set >= 25: >= 15 answerable, >= 5 unanswerable, >= 5 hard | `eval/golden.jsonl` (34), `eval/build_golden.py` | `test_golden_set_meets_the_assignment_minimums` | file | PASS |
| >= 8 human-written, labelled human/synthetic; >= 8 synthetic reviewed by hand | `author`, `reviewed` fields | 21 human (carried over from A2, group to confirm); 13 synthetic, `reviewed: false` | `eval/golden.jsonl` | PASS (10 synthetic questions hand-checked, all ok; 12 answers labelled, agreement 0.50: `eval/review/*_reviewed.jsonl`) |
| Module: >= 15 paraphrase vs >= 15 unrelated pairs, gap, time per chunk, determinism | `eval/embedding_pairs.json`, `ragops/evaluation/embedding_eval.py` | suite result | `eval/results/suite-baseline-*.json` | PASS |
| Component: recall@3/@5, MRR, nDCG@5 | `ragops/evaluation/retrieval_eval.py`, `common.py` | unit tests with known values; suite | suite result | PASS |
| Noise test (>= 3 irrelevant documents or typos), change reported | `retrieval_eval.noise_client`, `typo_query` (both done) | suite result `delta_vs_clean` | suite result | PASS |
| End-to-end: faithfulness, abstention, citation validity, p50/p95 | `ragops/evaluation/generation_eval.py` | suite | suite result | PASS (faithfulness is lexical, see report) |
| If an LLM judges, label >= 8 answers by hand and report agreement | not applicable: the judge is lexical, not an LLM | - | report states this | N/A |
| Seeds fixed, suite run twice, difference per metric explained | `ragops/evaluation/suite.py` (`--repeat 2`, `stochasticity`) | result file | `stochasticity` block | PASS |
| One command runs the suite, writes timestamped file + summary table | `python -m ragops.evaluation.suite` | run | `eval/results/suite-*.json/.md` | PASS |

## Part C: experiment and release gate

| Req | Implementation | Check | Evidence | Status |
| --- | --- | --- | --- | --- |
| C1 one change, suite on baseline and candidate, all three levels compared | `experiments/baseline`, `experiments/candidate/*.yaml` | suite results | `eval/results/suite-*` | see results |
| C2 thresholds in a config file; script applies gate, exit code; one failing, one passing | `config/release_thresholds.yaml`, `ragops/gate.py`, `experiments/release_gate.py` | `tests/test_tracing_and_eval.py` gate tests; real runs | gate output files | failing PASS; passing see results |
| C3 roll-out / rollback on Kubernetes | see F3 | | `F4`-`F6` | PASS |

## Part D: observability

| Req | Implementation | Check | Evidence | Status |
| --- | --- | --- | --- | --- |
| D1 one JSON line per query with all listed fields | `api/app/tracing.py`, wiring in `services/answer.py`, `retrieval/chroma.py`, `services/prompt.py` | `test_every_query_writes_a_complete_trace` | `traces/logs/eval/*.jsonl` | PASS |
| D2 tool: trace id -> exact context and prompt | `ragops/tracing/inspector.py` | `test_trace_inspector_rebuilds_the_exact_prompt` (hash match) | inspector output | PASS |
| D3 metrics: top-1 similarity, abstention rate, cache hit rate, p95 per stage, injections flagged; summary script | `ragops/tracing/summary.py`, `api/app/routes/metrics.py` (`/metrics`) | `test_summary_script...` | `traces/metrics/` | PASS (cache rate on the cluster) |
| D4 injection guardrail writes its action into the trace; tested with the Batch B document | `neutralise_injection` -> `tracing.guardrail` | `test_injection_in_a_passage_is_neutralised_and_logged`; Batch B run | trace | PASS (unit); real Batch B trace PENDING |
| D5 root cause from a trace only, 5 lines | `reports/evidence/D5-h05-evidence.md` | trace 3f951a96 | report section 3 | PASS (written in report; member 2 to confirm wording) |

## Part E: drift and coverage (member 2)

| Req | Implementation | Status |
| --- | --- | --- |
| E1 >= 40 live queries (34 in-domain, 6 outside) | `eval/live_queries/` | PARTIAL: 40 queries, but only 6 are outside the corpus (brief asks for about 12); AI-drafted, status pending-review |
| E2 coverage vs golden set, threshold justified, uncovered topics | `ragops/evaluation/coverage.py` (code by member 1) | PASS: coverage before 47.5%, after 52.5% (`eval/results/COVERAGE-before-vs-after.md`); 85% target not met |
| E3 ingest Batch B, re-run suite, report what changed and why | suite `--state AB`; golden `after_batch_b` | PASS: `eval/results/DRIFT-A-vs-AB.md` (golden h02 label needs an `after_batch_b` override: member 2) |
| E4 >= 6 new golden questions, coverage rises, non-zero exit below threshold | `coverage.py` exit code | PASS (n01-n06; 47.5% to 52.5%; exit non-zero because below 85%) |

## Part F: Kubernetes

| Req | Implementation | Status |
| --- | --- | --- |
| F1 API Deployment, vector store StatefulSet, Service, PVC for data lake, quarantine, archive | `k8s/40-api.yaml`, `30-chroma.yaml`, `10-storage.yaml` | PASS (deployed on minikube; `reports/evidence/F1-cluster-state.txt`) |
| F2 ingestion Job + CronJob (only writer); eval Job exits non-zero on gate fail; thresholds in ConfigMap | `k8s/ingest-job.yaml`, `ingest-cronjob.yaml`, `eval-job.yaml`, `jobs/eval-candidate*.yaml`, `20-configmaps.yaml` | PASS: Batch A/B and candidate ingested by Jobs, CronJob run by hand (0 chunks on unchanged input), baseline + 2 candidate evals, gate FAIL exits non-zero (Job Failed), threshold edit in the ConfigMap flipped the verdict (`F2-*`, `F3-*`). `eval-candidate-bad` manifest not run in cluster. No concurrent-writer test in cluster. |
| F3 candidate Deployment + Service + own collection; rolling update `maxUnavailable: 0`; rollout status; gate-stopped candidate; bad release undone; trace after undo shows previous collection | `k8s/41-api-candidate.yaml`, `40-api.yaml` | PASS (`F4`-`F6`): rolling update with `maxUnavailable: 0`, rollout status/history, gate-failed candidate not promoted, bad release reversed with `rollout undo`, new trace shows `collection: rahbar` and the embedding version again |
| F4 traces to stdout and volume; metrics via port-forward | `api/app/tracing.py`, `routes/metrics.py` | PASS: traces on stdout (read with `kubectl logs`) and on the traces PVC (copied to `traces/logs/k8s`); /metrics exists, port-forward command in `k8s/README.md` (scrape not captured as evidence) |
| F5 resource requests/limits from measurements | manifests | PARTIAL: API/Chroma/Redis measured with `crictl stats` (metrics-server broken here); Job peaks not measured (`F7`) |
| k8s/README.md with all commands | `k8s/README.md` | PASS |

## Part G and submission

| Req | Status |
| --- | --- |
| Report PDF <= 8 pages (Figure 3 table, Table 2 table, results + release decision, short answers a-f, contributions + AI statement) | PASS (4 pages; names, roll numbers and screenshots still PENDING) |
| Names and roll numbers on page 1 | PENDING (need from the group) |
| Screenshots appendix A-F | PENDING (text evidence captured by script; real screenshots need the group) |
| README with the command for each part A-F | PASS (`README.md`, "The commands, in execution order") |
| Commits from both members | PASS (`git log`: both members have commits) |
