# Evaluation suite: candidate-chunk200

2026-11-23T17:28:28Z | state **A** | collection `rahbar_c200` | provider `extractive` | top_k 5 | seed 20260301 | 29 golden questions | 2 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 2397.100 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.891 / 0.957 |
|  | MRR / nDCG@5 | 0.780 / 0.816 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.957 / 0.777 / 0.813 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.957 / 0.777 / 0.812 |
| End-to-end: answers | answer correctness | 0.609 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.130 |
|  | latency p50 / p95 (ms) | 109.250 / 716.370 |

## Run-to-run difference (2 runs, same seed)

Largest absolute difference over 65 quality metrics: **0.0**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |
| embedding.time_per_chunk_ms.p50 | 2014.7 | 3212.3 | 1197.6 |
| embedding.time_per_chunk_ms.max | 6171.7 | 6900.5 | 728.8 |
| embedding.time_per_chunk_ms.mean | 2397.1 | 3042.5 | 645.4 |
| generation.latency_ms_per_stage.total.p95 | 708.528 | 814.414 | 105.886 |
| generation.latency_ms.p95 | 716.37 | 820.482 | 104.112 |
| generation.latency_ms_per_stage.retrieval.p95 | 701.44 | 796.93 | 95.49 |
| generation.latency_ms_per_stage.total.max | 777.02 | 853.96 | 76.94 |
| generation.latency_ms.max | 778.13 | 855.01 | 76.88 |

Wrong or abstained answerable questions: ['q04', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h04', 'h05']
Unanswerable questions that were answered: none
