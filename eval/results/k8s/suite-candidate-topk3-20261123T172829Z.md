# Evaluation suite: candidate-topk3

2026-11-23T17:28:29Z | state **A** | collection `rahbar` | provider `extractive` | top_k 3 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 2264.200 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.913 / 0.913 |
|  | MRR / nDCG@5 | 0.855 / 0.861 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.913 / 0.833 / 0.845 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.913 / 0.826 / 0.839 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.217 |
|  | latency p50 / p95 (ms) | 116.620 / 486.608 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| generation.latency_ms.max | 4099.26 | 930.7 | 3168.56 |
| generation.latency_ms_per_stage.total.max | 4098.01 | 929.8 | 3168.21 |
| generation.latency_ms_per_stage.retrieval.max | 4071.6 | 925.05 | 3146.55 |
| embedding.time_per_chunk_ms.max | 6888.8 | 6146.5 | 742.3 |
| embedding.time_per_chunk_ms.mean | 2264.2 | 2692.3 | 428.1 |
| generation.latency_ms_per_stage.retrieval.p95 | 478.356 | 871.844 | 393.488 |
| generation.latency_ms.p95 | 486.608 | 875.912 | 389.304 |
| generation.latency_ms_per_stage.total.p95 | 485.632 | 873.888 | 388.256 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
