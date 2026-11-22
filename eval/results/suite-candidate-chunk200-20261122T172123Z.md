# Evaluation suite: candidate-chunk200

2026-11-22T17:21:23Z | state **A** | collection `rahbar_c200` | provider `extractive` | top_k 5 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 1447.200 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.891 / 0.957 |
|  | MRR / nDCG@5 | 0.780 / 0.816 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.957 / 0.777 / 0.813 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.957 / 0.777 / 0.812 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.130 |
|  | latency p50 / p95 (ms) | 39.300 / 244.424 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.max | 4932.8 | 1575.5 | 3357.3 |
| embedding.time_per_chunk_ms.mean | 1447.2 | 685.5 | 761.7 |
| embedding.time_per_chunk_ms.p50 | 887.6 | 602.7 | 284.9 |
| generation.latency_ms_per_stage.retrieval.max | 231.38 | 257.5 | 26.12 |
| generation.latency_ms_per_stage.total.p95 | 228.76 | 253.584 | 24.824 |
| generation.latency_ms_per_stage.retrieval.p95 | 227.04 | 251.132 | 24.092 |
| generation.latency_ms_per_stage.total.max | 235.99 | 259.72 | 23.73 |
| generation.latency_ms.max | 249.01 | 270.69 | 21.68 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
