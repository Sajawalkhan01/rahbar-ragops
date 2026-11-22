# Evaluation suite: baseline

2026-11-22T12:54:47Z | state **A** | collection `rahbar` | provider `extractive` | top_k 5 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 1723.500 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.913 / 0.913 |
|  | MRR / nDCG@5 | 0.855 / 0.861 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.913 / 0.833 / 0.845 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.913 / 0.826 / 0.839 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.174 |
|  | latency p50 / p95 (ms) | 53.670 / 604.398 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.p50 | 1264.8 | 1134.8 | 130.0 |
| embedding.time_per_chunk_ms.max | 6016.3 | 6146.2 | 129.9 |
| generation.latency_ms_per_stage.retrieval.max | 624.59 | 515.98 | 108.61 |
| generation.latency_ms_per_stage.total.max | 627.27 | 526.88 | 100.39 |
| generation.latency_ms.max | 643.5 | 544.14 | 99.36 |
| generation.latency_ms.p95 | 604.398 | 531.932 | 72.466 |
| embedding.time_per_chunk_ms.mean | 1723.5 | 1698.1 | 25.4 |
| generation.latency_ms_per_stage.total.p95 | 535.656 | 513.64 | 22.016 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
