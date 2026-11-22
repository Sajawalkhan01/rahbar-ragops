# Evaluation suite: baseline

2026-11-22T12:45:53Z | state **A** | collection `rahbar` | provider `extractive` | top_k 5 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 1689.300 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.913 / 0.913 |
|  | MRR / nDCG@5 | 0.855 / 0.861 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.913 / 0.833 / 0.845 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.913 / 0.826 / 0.839 |
| End-to-end: answers | answer correctness | 0.522 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.174 |
|  | latency p50 / p95 (ms) | 66.630 / 584.366 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| generation.latency_ms_per_stage.retrieval.max | 607.73 | 51.19 | 556.54 |
| generation.latency_ms_per_stage.total.max | 612.08 | 58.32 | 553.76 |
| generation.latency_ms_per_stage.retrieval.p95 | 548.268 | 44.538 | 503.73 |
| generation.latency_ms_per_stage.total.p95 | 555.272 | 56.874 | 498.398 |
| generation.latency_ms.p95 | 584.366 | 126.674 | 457.692 |
| generation.latency_ms.max | 632.82 | 230.15 | 402.67 |
| generation.latency_ms_per_stage.retrieval.mean | 131.59 | 32.82 | 98.77 |
| generation.latency_ms_per_stage.total.mean | 141.396 | 42.686 | 98.71 |

Wrong or abstained answerable questions: ['q03', 'q04', 'q09', 'q10', 'v01', 'v03', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
