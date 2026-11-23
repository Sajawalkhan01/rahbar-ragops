# Evaluation suite: candidate-chunk200

2026-11-23T17:35:10Z | state **A** | collection `rahbar_c200` | provider `extractive` | top_k 5 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 3011.400 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.891 / 0.957 |
|  | MRR / nDCG@5 | 0.780 / 0.816 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.957 / 0.777 / 0.813 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.957 / 0.777 / 0.812 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.130 |
|  | latency p50 / p95 (ms) | 74.500 / 711.868 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.max | 7647.5 | 3322.3 | 4325.2 |
| embedding.time_per_chunk_ms.mean | 3011.4 | 1243.7 | 1767.7 |
| embedding.time_per_chunk_ms.p50 | 2606.7 | 965.6 | 1641.1 |
| generation.latency_ms_per_stage.retrieval.max | 1555.7 | 1184.21 | 371.49 |
| generation.latency_ms.max | 1564.79 | 1199.95 | 364.84 |
| generation.latency_ms_per_stage.total.max | 1562.8 | 1198.23 | 364.57 |
| generation.latency_ms.p95 | 711.868 | 1011.72 | 299.852 |
| generation.latency_ms_per_stage.total.p95 | 710.652 | 1005.58 | 294.928 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
