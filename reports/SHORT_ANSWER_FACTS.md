# Facts for the short answers (a)-(f): for member 2 to turn into the group's own answers

These are verified facts with their sources, not the answers. The assignment asks for the group's own words.

**(a) Which check caught most in Batch B; which problem was not caught; what would catch it.**
Uniqueness caught 4 of 10 failures (exact copy, reformatted copy, draft near-duplicate, scholarship copy); quality 3, completeness 3, recency 1
(`eval/results/ingestion/verification-*batchB*.md`). Not caught: `library-rules-reworded.md` (same rules, reworded) passed all four checks and is
indexed next to the original; the injected `plagiarism-and-ai-guidance.md` also passed because injection is an advisory (policy `warn`), caught at
query time instead (`eval/results/DRIFT-A-vs-AB.md`). Think about: a semantic near-duplicate threshold on document-level embeddings, claim-level contradiction checks.

**(b) Module metric fine but component / end-to-end not.**
Embedding module: paraphrase pairs 0.887 vs unrelated 0.502, perfect separation, deterministic. Yet component level: hard questions recall@5 0.60,
and after Batch B i01/h03 MRR fell 1.0 to 0.5 (`DRIFT-A-vs-AB.md`). Also chunk-200: recall@5 up (0.913 to 0.957) while MRR fell (0.855 to 0.780).

**(c) Archive or delete old versions; what breaks on delete.**
Superseded versions are archived by metadata (`superseded=True`, `status=archived`) and the raw file is kept under `archive/`; rollback restores them
(`reports/evidence/A2-incremental-demo.txt`). Deleting the archive makes rollback impossible (re-ingest from the archive is the fallback path); deleting chunks of a
document leaves no orphans (audit). Reproducibility of old answers/traces also depends on the old version being present.

**(d) Metric trusted least.**
Faithfulness: it is lexical, and 1.0 by construction for an extractive generator (see the README limitations). Also answer correctness (word overlap with a reference)
and the tiny golden set (34; 23 retrieval questions) so one question moves recall by 0.043.

**(e) Hardest paper idea, and what changed.**
Your decision; facts: the paper's live-testing/coverage needs real traffic, which a student project does not have (live queries are written by hand);
the LLM spot check could not run on CPU (0/6 accepted, `eval/results/LLM-SPOTCHECK.md`), so the suite uses an extractive generator.

**(f) Which Kubernetes object carries which responsibility.**
Single writer: ingestion Job/CronJob only (mount `ragops-data` read-write, `RAGOPS_ROLE=ingestor`, writer lock, CronJob `concurrencyPolicy: Forbid`); the API Deployment does not mount the data PVC.
StatefulSet `chroma` + its PVC: vector store persistence. ConfigMap `ragops-config`: embedding model pinned once; ConfigMap `release-thresholds`: gate policy.
Eval Jobs: gate (exit non-zero stops release). Deployment `RollingUpdate` `maxUnavailable: 0` + `rollout undo` + `change-cause` annotations: release/rollback and revision history.
PVC `ragops-traces`: traceability. Candidate Deployment/Service on `rahbar_c200`: isolated candidate index. (`k8s/README.md`)
