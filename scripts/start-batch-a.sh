#!/usr/bin/env bash
# Reset local ingestion state (NOT the Chroma volume) and run Batch A.
cd "$(dirname "$0")/.." || exit 1
rm -rf data/quarantine data/state/ledger.* data/reports eval/results/ingestion
cp corpus/raw/fee-structure-page.html data/inbox/batch_a/ 2>/dev/null
setsid nohup bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_a --label "${1:-batchA-first}" > data/ingest-batchA.log 2>&1 < /dev/null &
echo started
