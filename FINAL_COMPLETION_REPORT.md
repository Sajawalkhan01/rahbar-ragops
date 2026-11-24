# Final completion report (member 1 side)

Status words: **PASS** = built and verified by a run whose output is committed. **PENDING** = not done, or needs a person.
Nothing below is marked PASS without an evidence file. Details per requirement: `A3_REQUIREMENTS_CHECKLIST.md`.

| Part | Status | Evidence | What is open |
| --- | --- | --- | --- |
| A Data management | **PASS** | `eval/results/ingestion/`, `reports/evidence/A1-*`, `A2-incremental-demo.txt`, `tests/test_ingestion.py` (19 tests) | Batch B hand review of dispositions (member 2) |
| B Offline testing | **PASS** | `eval/results/suite-baseline-*.json/.md` (run twice, quality diff 0.0) | Confirm golden labels, hand-review >= 8 synthetic questions (member 2); no LLM judge, so no judge-agreement step |
| C Experiment + gate | **PASS** | 3 candidates + bad; `gate-*.json`; cluster `F3-*` | none |
| D Observability | **PASS** | `traces/`, `D2`, `D3`, `D5-h05-evidence.md` | h05 bug (marker merges with next sentence) found, not fixed |
| E Drift and coverage | **PASS** (target not met) | `DRIFT-A-vs-AB.md`, `COVERAGE-before-vs-after.md`; 40 live queries, golden n01-n06 | coverage 52.5% against an 85% target; live queries are AI-drafted, not real traffic |
| F Kubernetes | **PASS** with stated gaps | `k8s/`, `k8s/README.md`, `reports/evidence/F1`-`F7` | no two-writer test in the cluster; Job resource peaks not measured; `eval-candidate-bad` not run in the cluster |
| G Report | **PARTIAL** | `reports/assignment_03_report.pdf` (4 pages), `reports/build_report.py` | names and roll numbers, human review verdicts, real screenshots |

## The 12 points

1. **What was built.** The A2 RAHBAR pipeline plus a RAGOps layer: verified, incremental, versioned ingestion; a three-level evaluation suite; a configurable release gate; per-query traces and a trace tool; query coverage checker; Kubernetes manifests with Jobs, rolling update, rollback.
2. **What was reused unchanged from A2.** Retrieval (dense + BM25 + exact-term fusion), prompt and answer validation, semantic cache, FastAPI, Prometheus. A2 additions are small and marked (tracing, query-time injection logging, an extractive provider).
3. **How to run it.** `README.md` (commands per part) and `k8s/README.md`.
4. **What was verified by running.** Parts A to D on real Chroma + Ollama; the whole of Part F on minikube. 55 A3 unit tests pass (run again at the end of this session) (A2's suites were not re-run in this session).
5. **Headline results.** Batch B: 8 PASS / 10 FAIL. Baseline recall@5 0.913, MRR 0.855, nDCG@5 0.861, answer correctness 0.609. chunk-200 rejected (MRR -0.075), top_k 3 released, bad candidate rejected. Same quality numbers inside and outside the cluster.
6. **What was changed during the work because a test failed.** A quarantined duplicate used to block its identical original (found by running the incremental demo; fixed + regression test). The ingest Jobs had no writable `/traces` (found on the first cluster run; fixed). The sentence splitter broke on "Rs. 12,000" (fixed; the earlier run is kept in `eval/results/history/`).
7. **What is weaker than it looks.** Faithfulness is lexical and 1.0 by construction (extractive generator). The golden set is small (34), so single questions move metrics by about 0.04. The gate passed top_k 3 although false abstentions rose from 0.174 to 0.217. The reworded duplicate and the injected note pass verification.
8. **The real-LLM check.** `llama3.2:3b` on CPU: 0 of 6 answers accepted (about 3 minutes each, output validation rejected the replies). The cause was not analysed. All suite numbers use the extractive provider.
9. **Image build.** The standard `Dockerfile` did not finish on this network (pip/apt timeouts), so it is **unverified**. The deployed image comes from `Dockerfile.local` / `scripts/build-image-local.sh`, using the tested virtualenv, without tesseract/poppler: **no OCR inside the cluster**. Before the demo, run `docker build -t ragops:v1 .` once on a good network.
10. **Cluster limits.** `kubectl top` failed (metrics-server could not scrape the kubelet), so API/Chroma/Redis use was read with `crictl stats`; Job peaks were not measured. Limits are therefore sufficient (no OOM, no restarts), not tuned.
11. **Collaboration.** Work went through pull requests #1-#4 from `Sajawalkhan01`, each approved and merged by `abdy879`. Earlier commits were pushed to `main` directly before the rule was set; that cannot be undone without a force-push.
12. **What still needs people.** Everything marked PENDING above, the real screenshots, names and roll numbers, a check that the committed files contain no secrets (none were added; `.env.example` has placeholders only), and one clean `docker build`.
