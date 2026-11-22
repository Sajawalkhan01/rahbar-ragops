#!/usr/bin/env bash
# Run the release gate for a candidate result and show the process exit code.
#   bash scripts/gate-demo.sh candidate-bad
cd "$(dirname "$0")/.." || exit 1
bash scripts/w.sh python experiments/release_gate.py --baseline 'eval/results/suite-baseline-*.json' \
  --candidate "eval/results/suite-${1}-*.json" --out "eval/results/gate-${1}-verdict.json"
code=$?
echo "process exit code: ${code}"
exit $code
