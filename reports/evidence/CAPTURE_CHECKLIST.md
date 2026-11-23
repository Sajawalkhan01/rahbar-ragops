# Screenshots to take (the assignment requires real terminal screenshots from your own cluster and runs)

Nothing here was screenshotted by the assistant. Each row gives the command; run it, screenshot the terminal with the
command and its full output visible, label it with the item code, and paste it into the report appendix.
`reports/evidence/*.txt` already holds the unmodified output of these runs, so you can compare, but a text file is not a screenshot.

| Label | Command (run in WSL from the repo root, minikube running) | Text evidence already committed |
| --- | --- | --- |
| A1 | `cat eval/results/ingestion/verification-*batchB-first.md` | same file |
| A2 | `kubectl create job ingest-cron-manual-2 --from=cronjob/ingest-cron -n ragops` then `kubectl logs job/ingest-cron-manual-2 -n ragops` (shows 0 chunks embedded) | F2-cronjob-manual-run.txt |
| B | `cat eval/results/suite-baseline-*.md` | same file |
| C1 (gate fails) | `kubectl get job eval-candidate-topk3 -n ragops` / the chunk-200 Job log: see F3-gate-fail-chunk200-job.txt (re-create: edit ConfigMap back, `kubectl delete job eval-candidate -n ragops; kubectl apply -f k8s/jobs/eval-candidate.yaml`) | F3-gate-fail-chunk200-job.txt |
| C2 (gate passes) | `kubectl logs job/eval-candidate-topk3 -n ragops \| grep -A14 "RELEASE GATE"` | F3-gate-pass-topk3-job.txt |
| D1 | `kubectl logs -n ragops -l app=api --tail=200 \| grep '"type": "trace"' \| tail -1` | traces/logs/k8s/ |
| D2 | `bash scripts/w.sh python -m ragops.tracing.inspector <trace_id> --dir traces/logs` | D2-trace-inspector-guardrail.txt |
| E | `bash scripts/w.sh python -m ragops.evaluation.coverage --label before` and `--label after` | pending: needs live queries (member 2) |
| F1 | `kubectl get all,pvc,configmap,cronjob,job -n ragops` | F1-cluster-state.txt |
| F2 | `kubectl logs job/ingest -n ragops \| tail`, `kubectl logs job/eval -n ragops \| tail` | F2-ingest-batch-a-job.txt |
| F3 | `bash scripts/k8s-threshold-demo.sh relax`, rerun the candidate Job, show the verdict, then `restore` | F2-threshold-change-gate-pass.txt |
| F4 | `bash scripts/k8s-release-demo.sh bad` then `undo` (shows rollout status, undo, trace with collection and embedding version) | F5, F6 |
