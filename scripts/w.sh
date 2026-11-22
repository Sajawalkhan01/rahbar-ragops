#!/usr/bin/env bash
# Run a command inside the project env:  bash scripts/w.sh python -m ragops.ingestion status
cd "$(dirname "$0")/.." || exit 1
source scripts/dev-env.sh
cmd="$1"; shift
if [ "$cmd" = python ]; then cmd="$PY"; fi
exec "$cmd" "$@"
