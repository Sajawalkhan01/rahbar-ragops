# Evaluation suite: llm_spotcheck

2026-11-23T14:27:48Z | state **AB** | collection `rahbar` | provider `ollama-host` | top_k 5 | seed 20260301 | 6 golden questions | 1 runs

| Level | Metric | Value (run 1) |
| --- | --- | --- |
| Module: embedding | mean cosine, paraphrase pairs | 0.887 |
|  | mean cosine, unrelated pairs | 0.502 |
|  | gap (paraphrase - unrelated) | 0.384 |
|  | time per chunk (mean ms) | 979.600 |
|  | determinism: max abs difference | 0.000 |
| Component: retrieval | recall@3 / recall@5 | 1.000 / 1.000 |
|  | MRR / nDCG@5 | 1.000 / 1.000 |
|  | noise: irrelevant docs, recall@5 / MRR / nDCG@5 | 1.000 / 1.000 / 1.000 |
|  | noise: typos, recall@5 / MRR / nDCG@5 | 1.000 / 1.000 / 1.000 |
| End-to-end: answers | answer correctness | 0.000 |
|  | faithfulness (lexical support) | n/a |
|  | citation validity | n/a |
|  | abstention correctness / false abstentions | n/a / 1.000 |
|  | latency p50 / p95 (ms) | 187401.750 / 192429.997 |

## Run-to-run difference (1 runs, same seed)

Largest absolute difference over 0 quality metrics: **None**. Latency and timing metrics differ naturally.

| Metric | run 1 | run 2 | abs diff |
| --- | --- | --- | --- |

Wrong or abstained answerable questions: ['q01', 'q02', 'q03', 'q04', 'q05', 'q06']
Unanswerable questions that were answered: none
