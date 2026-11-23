# Evaluation suite: candidate-topk3

2026-11-22T17:23:36Z | state **A** | collection `rahbar` | provider `extractive` | top_k 3 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 933.100 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.913 / 0.913 |
|  | MRR / nDCG@5 | 0.855 / 0.861 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.913 / 0.833 / 0.845 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.913 / 0.826 / 0.839 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.217 |
|  | latency p50 / p95 (ms) | 38.570 / 256.816 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.max | 3294.7 | 3486.9 | 192.2 |
| generation.latency_ms.max | 279.43 | 239.64 | 39.79 |
| generation.latency_ms_per_stage.total.max | 257.44 | 229.79 | 27.65 |
| generation.latency_ms.p95 | 256.816 | 238.896 | 17.92 |
| generation.latency_ms_per_stage.retrieval.max | 243.82 | 226.97 | 16.85 |
| generation.latency_ms_per_stage.total.p95 | 243.174 | 226.716 | 16.458 |
| generation.latency_ms_per_stage.retrieval.p95 | 240.774 | 225.004 | 15.77 |
| embedding.time_per_chunk_ms.p50 | 635.1 | 650.8 | 15.7 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
