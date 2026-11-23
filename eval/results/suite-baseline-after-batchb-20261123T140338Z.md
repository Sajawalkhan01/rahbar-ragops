# Evaluation suite: baseline-after-batchb

2026-11-23T14:03:37Z | state **AB** | collection `rahbar` | provider `extractive` | top_k 5 | seed 20260301 | 34 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 1058.900 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.839 / 0.839 |
|  | MRR / nDCG@5 | 0.762 / 0.780 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.839 / 0.762 / 0.780 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.839 / 0.756 / 0.775 |
| End-to-end: answers | answer correctness | 0.679 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.179 |
|  | latency p50 / p95 (ms) | 38.935 / 226.310 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.max | 3668.3 | 3170.8 | 497.5 |
| embedding.time_per_chunk_ms.p50 | 749.2 | 621.0 | 128.2 |
| generation.latency_ms.max | 233.62 | 298.03 | 64.41 |
| generation.latency_ms_per_stage.total.max | 222.59 | 285.47 | 62.88 |
| generation.latency_ms_per_stage.retrieval.max | 220.24 | 282.74 | 62.5 |
| generation.latency_ms_per_stage.retrieval.p95 | 209.201 | 227.849 | 18.648 |
| generation.latency_ms_per_stage.total.p95 | 212.548 | 229.57 | 17.022 |
| embedding.time_per_chunk_ms.mean | 1058.9 | 1075.2 | 16.3 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
