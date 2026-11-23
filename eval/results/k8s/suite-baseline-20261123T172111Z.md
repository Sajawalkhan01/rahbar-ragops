# Evaluation suite: baseline

2026-11-23T17:21:11Z | state **A** | collection `rahbar` | provider `extractive` | top_k 5 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 13166.400 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.913 / 0.913 |
|  | MRR / nDCG@5 | 0.855 / 0.861 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.913 / 0.833 / 0.845 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.913 / 0.826 / 0.839 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.174 |
|  | latency p50 / p95 (ms) | 695.840 / 4397.600 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.max | 36762.4 | 7357.8 | 29404.6 |
| embedding.time_per_chunk_ms.p50 | 12305.1 | 1485.7 | 10819.4 |
| embedding.time_per_chunk_ms.mean | 13166.4 | 2360.9 | 10805.5 |
| generation.latency_ms.max | 5700.63 | 539.38 | 5161.25 |
| generation.latency_ms_per_stage.total.max | 5594.41 | 538.38 | 5056.03 |
| generation.latency_ms.p95 | 4397.6 | 506.098 | 3891.502 |
| generation.latency_ms_per_stage.retrieval.max | 4424.18 | 532.78 | 3891.4 |
| generation.latency_ms_per_stage.total.p95 | 4384.356 | 505.078 | 3879.278 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
