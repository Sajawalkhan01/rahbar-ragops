"""D5 evidence: why did question h05 abstain after Batch B?

Re-computes, for the retrieved context stored in trace 3f951a96..., the word-overlap score the extractive
provider (api/app/providers/llm/extractive.py) gives every sentence, using the provider's own tokenizer,
injection filter and sentence splitter. The provider answers only if a sentence reaches 0.34.

    PYTHONPATH=.:indexer:api python scripts/d5_h05_overlap.py > reports/evidence/D5-h05-overlap-output.txt
"""
import json

from app.providers.llm.extractive import _sentences
from app.retrieval.bm25 import exact_terms, tokenize
from app.services.prompt import _FENCE, neutralise_injection

TRACE_ID = "3f951a96"
Q = "What does the university count as plagiarism in coursework?"
THRESHOLD = 0.34
qw = set(tokenize(Q))
print("question tokens:", sorted(qw), "| exact terms:", exact_terms(Q), "| answer threshold:", THRESHOLD)
trace = next(json.loads(x) for x in open("traces/logs/eval/traces-local-20261123.jsonl", encoding="utf8")
             if TRACE_ID in x)
rows = []
for c in trace["context"]:
    clean = neutralise_injection(_FENCE.sub(" ", c["text"]), c["chunk_id"])
    heading = set(tokenize(c["text"].split("\n")[0]))
    for s in _sentences(clean):
        words = set(tokenize(s)) | heading
        rows.append((len(qw & words) / len(qw), c["chunk_id"], sorted(qw & words), s))
print("\nTop sentences by overlap (provider skips any sentence that contains the removal marker):")
for ov, cid, hit, s in sorted(rows, key=lambda r: -r[0])[:6]:
    print(f"{ov:.2f}  {cid}  {hit}\n      {s[:200]}")
print("\nSentences at or above the threshold:", sum(1 for r in rows if r[0] >= THRESHOLD))
