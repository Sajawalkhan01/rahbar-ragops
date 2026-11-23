# Data drift: suite in state A (Batch A only) vs state AB (Batch B ingested)

Same code, same config (`experiments/baseline/baseline.yaml`), same seed (20260301), extractive provider, collection `rahbar`.
- State A: `suite-baseline-20261122T125448Z.json` (23 retrieval questions, 29 generation questions)
- State AB: `suite-baseline-after-batchb-20261123T140338Z.json` (28 and 34; the 5 `h06`-`h10` questions need Batch B documents)

**The aggregates are not comparable on their own.** The question set grew by 5, so every average changed even where nothing moved.
The table below compares only the 23 questions present in both states. All figures come from the two result files.

| Metric (clean retrieval) | State A (23 q) | State AB (28 q, as reported) |
| --- | --- | --- |
| recall@5 | 0.913 | 0.839 |
| MRR | 0.855 | 0.762 |
| nDCG@5 | 0.861 | 0.780 |
| answer correctness | 0.609 | 0.679 |

## What changed on the 23 common questions

| Question | Change | Cause | Is it a regression? |
| --- | --- | --- | --- |
| q04 (security deposit) | top-1 moved from `fee-structure-page.html` to `fee-structure-2027-28.md`; nDCG@5 0.92 to 1.00 | newer fee version now active, the 2026-27 version is archived and filtered out | No. This is intended drift. Golden `after_batch_b` overrides expect it. |
| e02 (misc. fees) | top-1 now `fee-structure-2027-28.md` (score 0.667 to 0.735) | same | No |
| h02 (withdraw deadline + fee) | recall@5 0.5 to 0.0, MRR 0.33 to 0 | the fee half of the answer is now in `fee-structure-2027-28.md`, but golden still names `fee-structure-page.html` | **Golden label is stale**, not a retrieval fault. h02 needs an `after_batch_b` override (golden curation, for the reviewer). |
| i01 (CGPA, injection question) | MRR 1.0 to 0.5 | top-1 is now the new `plagiarism-and-ai-guidance.md` chunk (it holds the injected "CGPA ... is 1.0" sentence), ahead of handbook page 24 | **Yes, real.** The injected document displaces the right chunk; the right chunk is still rank 2. |
| h03 (CGPA for academic warning) | MRR 1.0 to 0.5 | top-1 is now another handbook chunk (section 1.25 Minimum CGPA, page 10); page 24 dropped to rank 2. Cause not investigated further. | Yes, real (rank order only). |
| h05 (plagiarism) | answered before, abstains now | top-1 is now the plagiarism guidance chunk (score 0.7386) instead of the handbook code-of-conduct chunk. The generator then abstains. Exact reason not yet analysed (see trace `3f951a96...`) | **Yes, real.** Candidate for the D5 root-cause write-up. |

## The injected document is neutralised at query time
`plagiarism-and-ai-guidance.md` was admitted (injection is an advisory in verification, by policy), so the query-time guardrail is what protects answers.
In `traces/logs/eval/traces-local-20261123.jsonl` there are 10 `injection_sentence_removed` events for chunk `plagiarism-and-ai-guidance-0001` and
26 `question_injection_flagged` events. No unanswerable question was answered ("Unanswerable questions that were answered: none").
Inspector output for a trace: `reports/evidence/D2-trace-inspector-guardrail.txt`. Metrics summary: `traces/metrics/summary.json`.

## Caveats
- Answer correctness rose (0.609 to 0.679) mostly because the 5 new questions are easy, not because anything improved.
- The two runs inside this suite differ only in latency and embedding timings (see the stochasticity block in the result file).
- Extractive generator: faithfulness is high by construction. Do not read the answer metrics as LLM quality.
