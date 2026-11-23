# Session handoff (Assignment 03, RAGOps / RAHBAR)

Written 2026-11-23 so work can resume in a new chat. Read this first, then `A3_REQUIREMENTS_CHECKLIST.md`.

## Goal
Complete FAST-NUCES SCD Assignment 03 (RAGOps) by extending the A2 RAHBAR RAG project. The official `Assignment_03.pdf` is the final authority.
Parts: A ingestion/verification, B evaluation suite, C experiment + release gate, D traces/metrics, E coverage, F Kubernetes (minikube), G report PDF (max 8 pages).
Hard rules: never fabricate results, screenshots or deployments. No secrets in git. Docker Compose is not a substitute for Kubernetes. Claim K8s success only if actually deployed and verified.

- Repo: https://github.com/Sajawalkhan01/rahbar-ragops (local: `D:\SEMESTER 5\SCD\A3\Assignment-03-RAGOps`)
- A2 originals (untouched): `D:\SEMESTER 5\SCD\A3\A2-rahbar.zip`
- Two members: Sajawalkhan01 (Part A, B, C, D, F + report machinery) and abdy879 (Abdi: Part E data, golden-set review, report text, screenshots).

## Working rules the user set
1. No Claude/AI attribution anywhere (commits, PR bodies, GitHub). No Co-Authored-By, no "Generated with Claude Code". Commits are authored as Sajawalkhan01.
2. Never use abdy879's credentials. Abdi's commits and approvals are done by Abdi himself; give him commands.
3. Never push straight to `main`. Use a feature branch and a pull request, approved by the other member.
4. Do Sajawal's part first, then STOP before Abdi's part.

## State of the work
Done and verified (real Chroma and Ollama, in WSL):
- Part A: verification (quality, completeness, recency, uniqueness, plus an injection advisory), quarantine, ledger, incremental ingest, archive and rollback, orphan audit. Batch A and Batch B reports. Batch B result: 8 PASS, 10 FAIL; the reworded library duplicate passed all four checks.
- Incremental demo (`scripts/demo-incremental.sh`): unchanged re-run embeds 0 chunks; modify embeds 1; delete leaves 0 orphans; a newer version archives the old one; rollback restores it.
- Bug found and fixed: a quarantined duplicate blocked its identical original (blocked by sha). Fix in `Quarantine.blocked()` with a regression test.
- Part B: golden set (34), embedding, retrieval and end-to-end suite, run twice with zero diff, one command.
- Part C: baseline, plus three candidates. `candidate-bad` fails the gate and `candidate-chunk200` fails it (recall@5 up, MRR down). `candidate-topk3` passes. Caveat: false abstentions rose from 0.174 to 0.217 and the gate does not catch that.
- Part D machinery: JSONL traces, inspector (prompt-hash MATCH), summary, guardrail logging. Tests are green.

Git:
- Earlier work was pushed straight to `main` before the PR rule was stated. It is not undone (it would need a force-push, which needs the user's OK).
- PR #1 (https://github.com/Sajawalkhan01/rahbar-ragops/pull/1) is open from branch `feat/part-a-c-results`. It holds the bug fix, the demo script, results, traces and evidence.
- abdy879 is NOT yet a repo collaborator, so he cannot be requested as reviewer. The user must invite him (Settings > Collaborators), then he approves PR #1. Recommended: protect `main` and require 1 approval.
- This file (`SESSION_HANDOFF.md`) is not committed. Commit it on a new feature branch if wanted.

## Remaining work (Sajawal's side, each as its own branch + PR)
1. Batch B drift run: ingest Batch B into the main collection, re-run the suite (`--state auto` detects AB), and analyse the change (fee drift in q04 and e02). Capture a real Batch B guardrail/injection trace and run the inspector on it. Run `ragops.tracing.summary` into `traces/metrics/`.
2. Real-LLM spot check: ollama-host `llama3.2:3b`, `--limit ~6`, label `llm_spotcheck`. Report it separately from the extractive suite.
3. Part F on minikube:
   - Build `ragops:v1` (`docker build -t ragops:v1 .` in WSL).
   - Start minikube (about `--memory=3500 --cpus=3`). Host Ollama must listen on 0.0.0.0, reached at host.minikube.internal:11434.
   - `minikube image load ragops:v1`, then `kubectl apply -k k8s/`.
   - Load the inbox via a loader pod. Run the ingest Job (Batch A to `rahbar`, candidate to `rahbar_c200`, then Batch B).
   - Run the eval Job (exits non-zero on gate fail). Show the candidate gate FAIL stopping the rollout. Show that editing the `release-thresholds` ConfigMap changes the outcome.
   - Rolling update (maxUnavailable 0) with a passing candidate (topk3).
   - A deliberately bad release reversed with `kubectl rollout undo`, plus a new trace showing the previous collection/embedding version.
   - Measure `kubectl top` for resource requests/limits.
   - Capture `kubectl get all,pvc,configmap,cronjob,job`, logs, and rollout status/undo output.
   - Write `k8s/README.md`. The single-writer design: `RAGOPS_ROLE=ingestor`, a file lock, only the Job mounts the data PVC, and CronJob `concurrencyPolicy: Forbid`.
4. Report machinery: `reports/assignment_03_report.pdf` (max 8 pages, placeholders for names, roll numbers, contributions, AI statement, short answers), `reports/evidence/CAPTURE_CHECKLIST.md`, `FINAL_COMPLETION_REPORT.md` (Parts A-G PASS/FAIL/PENDING plus the 12 explanation items), update `A3_REQUIREMENTS_CHECKLIST.md` and `A3_IMPLEMENTATION_PLAN.md` (phase table is stale), delete leftover `_extract/`.
5. Then STOP.

## Abdi's part (not started; give him commands, he pushes from his own account)
- Live queries: at least 40 in `eval/live_queries/live_queries.jsonl`; run `python -m ragops.evaluation.coverage --label before`; add at least 6 new golden questions; run coverage `--label after`.
- Golden set: confirm human labels, hand-review at least 8 synthetic questions (`python -m ragops.evaluation.review_sheet golden`), label about 12 answers (`... answers <suite.json>`, then `... agreement`).
- Review Batch B results and write the D5 root-cause analysis from a real trace.
- Report: short answers a-f, contribution table, 2-3 line AI statement, names and roll numbers.
- Take the real screenshots (appendix A-F); text evidence is in `reports/evidence/*.txt`.

## Environment notes
- Windows host + WSL. Use `bash scripts/w.sh <cmd>` for WSL commands (`$` gets mangled through `wsl.exe`). Use the Write tool for large files (Git Bash breaks on big heredocs). Use `setsid nohup ... < /dev/null &` for detached jobs. Use the `[r]` bracket trick with pkill.
- Dev stack: Chroma 1.0.12 in Docker (port 8000), Ollama (`nomic-embed-text`, `llama3.2:3b`) on port 11434, venv `~/rahbar-venv`. Setup is in `README.md`.
- Tests: `bash scripts/w.sh python -m pytest tests -q`.
- Full earlier transcript: `C:\Users\Muhammad Sajawal Kha\.claude\projects\d--SEMESTER-5-SCD-A3\a5bdb035-8299-4b67-be22-6e0ab26d2cbe.jsonl`
