#!/usr/bin/env bash
# Build the candidate collection (chunk 200 / overlap 25) from Batch A, detached.
cd "$(dirname "$0")/.." || exit 1
export CHROMA_COLLECTION=rahbar_c200 CHUNK_SIZE=200 CHUNK_OVERLAP=25
setsid nohup bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_a --label candidate-c200 > data/ingest-candidate.log 2>&1 < /dev/null &
echo started
