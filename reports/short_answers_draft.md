# Short answers (a)-(f): DRAFT for abdy879 to edit

**Status: draft written by the AI assistant from `reports/SHORT_ANSWER_FACTS.md`. Not the group's final answers.**
Edit every answer until it says what the group actually believes, then paste it into `reports/build_report.py` (`SHORT_ANSWERS`).
Facts and file names below were taken from committed results; check any number you keep.

## (a) Which Batch B check caught the most, which problem got through, and what would catch it?

Uniqueness caught the most: 4 of the 10 failures (the exact copy, the reformatted copy, the draft near-duplicate and the
scholarship copy). Quality and completeness caught 3 each, recency 1. One problem got through: `library-rules-reworded.md` says
the same rules in different words, passed all four checks and is now indexed next to the original. The injected
`plagiarism-and-ai-guidance.md` also passed, because injection is only an advisory in our policy; it was caught at query time
instead. A document-level embedding similarity check would catch the reworded duplicate, and a claim-level contradiction
check would be needed to catch conflicting versions of the same rule.

## (b) A module metric looked fine but the component or end-to-end result did not

The embedding module separated paraphrase pairs (0.887 similarity) from unrelated pairs (0.502) perfectly and deterministically.
At component level, recall@5 on hard questions was only 0.60, and after Batch B the rank of the right chunk for `i01` and `h03`
fell from 1 to 2 (MRR 1.0 to 0.5). The chunk-200 candidate shows the same gap: recall@5 rose (0.913 to 0.957) while MRR
fell (0.855 to 0.780), so the module-level number said "better" and the end result got worse.

## (c) Archive or delete old versions? What breaks on delete?

We archive. A superseded version is kept as metadata (`superseded=True`, `status=archived`) with the raw file under `archive/`,
and rollback restores it (`reports/evidence/A2-incremental-demo.txt`). If the archive were deleted, rollback would no longer be
possible and old answers and traces could not be reproduced, because the version they cite would be gone.

## (d) Which metric do you trust least, and why?

Faithfulness. It is a lexical overlap score, and with the extractive generator it is 1.0 by construction, because every
answer is copied from the context. Answer correctness (word overlap with a reference) is also weak, and the golden set is small
(34 at the time of the baseline; 23 retrieval questions), so one question moves recall@5 by about 0.04.

## (e) Which paper idea was hardest to apply, and what did you change? **Write this one yourself.**

Facts you can use, if they match your view: live-traffic testing and coverage need real users, and we had none, so live queries were
written by hand and the coverage result (47.5% to 52.5%, below the 85% target) says more about our drafted queries than about
real usage. The real-LLM check could not run usefully on a CPU (0 of 6 answers accepted, `eval/results/LLM-SPOTCHECK.md`), so the
suite uses a deterministic extractive generator. Say which of these, or something else, was hardest for you, and what you did.

## (f) Which Kubernetes object carries which responsibility?

* **Single writer:** only the ingestion Job and CronJob mount the data volume read-write and set `RAGOPS_ROLE=ingestor`;
  the CronJob uses `concurrencyPolicy: Forbid`. The API Deployment does not mount that volume.
* **StatefulSet `chroma` and its PVC:** vector store persistence.
* **ConfigMap `ragops-config`:** the embedding model, stated once for every pod. **ConfigMap `release-thresholds`:** the gate policy.
* **Evaluation Jobs:** the gate (a failing gate makes the Job fail, which stops the release).
* **API Deployment with `RollingUpdate`, `maxUnavailable: 0`:** releases without downtime; `rollout undo` and the change-cause
  annotations give rollback and revision history.
* **PVC `ragops-traces`:** traceability. **Candidate Deployment and Service on `rahbar_c200`:** an isolated candidate index.

Known limit to mention: a two-writers-at-once test was not run in the cluster.
