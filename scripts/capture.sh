#!/usr/bin/env bash
# Evidence capture: run a command and store the command, UTC time, exit code and its UNMODIFIED output.
#   bash scripts/capture.sh A1-verification-batch-b "bash scripts/w.sh python -m ragops.ingestion run --inbox data/inbox/batch_b"
# Writes reports/evidence/<id>.txt and also prints the output. These text files are the evidence the report
# appendix quotes; real terminal screenshots of the same commands still have to be taken by the group
# (reports/evidence/CAPTURE_CHECKLIST.md lists which).
id="$1"; shift
cmd="$*"
cd "$(dirname "$0")/.." || exit 1
mkdir -p reports/evidence
out="reports/evidence/${id}.txt"
{
  echo "# evidence ${id}"
  echo "# captured: $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(hostname)"
  echo "\$ ${cmd}"
} > "$out"
bash -c "${cmd}" > >(tee -a "$out") 2>&1
code=$?
echo "# exit code: ${code}" | tee -a "$out"
exit $code
