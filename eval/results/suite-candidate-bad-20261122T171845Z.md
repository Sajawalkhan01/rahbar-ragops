# Evaluation suite: candidate-bad

2026-11-22T17:18:45Z | state **A** | collection `rahbar` | provider `extractive` | top_k 1 | seed 20260301 | 29 golden questions | 1 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 19104.000 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 0.913 / 0.913 |
|  | MRR / nDCG@5 | 0.855 / 0.861 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 0.913 / 0.833 / 0.845 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 0.913 / 0.826 / 0.839 |
| End-to-end: answers | answer correctness | 0.391 |
|  | faithfulness (lexical support) | 1.000 |
|  | citation validity | 1.000 |
|  | abstention correctness / false abstentions | 1.000 / 0.522 |
|  | latency p50 / p95 (ms) | 34.150 / 268.314 |

## Run-to-run difference (1 runs, same seed)

Largest absolute difference over 0 quality metrics: **None**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |

Wrong or abstained answerable questions: ['q04', 'q05', 'q06', 'q07', 'q09', 'q10', 'v01', 'e03', 'i01', 'h01', 'h02', 'h03', 'h04', 'h05']
Unanswerable questions that were answered: none
