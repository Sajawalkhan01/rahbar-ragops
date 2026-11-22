#!/usr/bin/env bash
# Part A2 demo on REAL Chroma + Ollama, in an isolated collection (rahbar_demo) so the main index is untouched.
#   bash scripts/demo-incremental.sh
# Scenarios: first ingestion, unchanged re-run (0 chunks), modify one document, add a document, delete a document
# (orphan count by document id), add a newer version (old one archived), rollback (old one restored).
cd "$(dirname "$0")/.." || exit 1
export CHROMA_COLLECTION=rahbar_demo RAGOPS_ROLE=ingestor
INBOX=data/inbox/demo
RUN="bash scripts/w.sh python -m ragops.ingestion"
count() { bash scripts/w.sh python - <<'PY'
import json,sys
from ragops.vectorstore import get_reader
import os
c=get_reader().get_collection(os.environ["CHROMA_COLLECTION"])
rows=c.get(include=["metadatas"])
by={}
for m in rows["metadatas"]:
    k=(m["doc_id"], m["status"], "superseded="+str(m["superseded"]))
    by[k]=by.get(k,0)+1
for k,v in sorted(by.items()): print(f"    {k[0]:28} {k[1]:9} {k[2]:17} chunks={v}")
PY
}
step() { echo; echo "=== $1"; }
summary() { grep -E '^\{"run_id"' | tail -1; }

rm -rf "$INBOX" && mkdir -p "$INBOX"
# fresh start for this collection
bash scripts/w.sh python - <<'PY'
import os
from ragops.vectorstore import get_reader
try: get_reader().delete_collection(os.environ["CHROMA_COLLECTION"])
except Exception: pass
PY
rm -f data/state/ledger.rahbar_demo.json
B=eval/batch_b
cp $B/library-rules.md $B/examination-rules-faq.md $B/course-withdrawal-guide.md "$INBOX"/
# fee v1 (2026-27) as a Markdown copy of the A2 fee page text, same family as the 2027-28 file
sed -e 's/Fee Structure 2027-28/Fee Structure 2026-27/' -e 's/doc_version: 2027-28/doc_version: 2026-27/' \
    -e 's/date: 2027-06-01/date: 2026-06-01/' -e 's/32,000/30,000/' -e 's/13,500/12,000/g' \
    -e 's/Fall 2027/Fall 2026/' -e 's/2027-28/2026-27/' $B/fee-structure-2027-28.md > "$INBOX/fee-structure-2026-27.md"

step "1. first ingestion of 4 documents"
$RUN run --inbox $INBOX --label demo1 | summary; count
step "2. same inbox again, nothing changed: expect chunks_embedded 0"
$RUN run --inbox $INBOX --label demo2 | summary
step "3. modify ONE document (exam FAQ: ten -> fifteen minutes): only its changed chunk is embedded"
sed -i 's/at least ten minutes before/at least fifteen minutes before/' "$INBOX/examination-rules-faq.md"
$RUN run --inbox $INBOX --label demo3 | summary
step "4. add a completely NEW document (scholarship policy): only it is indexed"
cp $B/scholarship-policy-2026.md "$INBOX"/
$RUN run --inbox $INBOX --label demo4 | summary
step "5. delete a document (library rules): its chunks must be gone, no orphans"
rm "$INBOX/library-rules.md"
$RUN run --inbox $INBOX --label demo5 | summary
echo "  audit after delete:"; $RUN audit | grep -E '"consistent"|"orphan_chunks"'
step "6. add a NEWER version of the fee document (2027-28): the 2026-27 version is archived (superseded=True)"
cp $B/fee-structure-2027-28.md "$INBOX"/
$RUN run --inbox $INBOX --label demo6 | summary; count
step "7. rollback: restore fee 2026-27 as the active version"
$RUN rollback --family fee-structure --to 2026-27 | grep -E 'restored|method|chunks_active'
count
step "ledger"
$RUN status
