"""Builds reports/assignment_03_report.pdf from numbers that are written here next to the file they came from.

    python reports/build_report.py

Parts that only the group can supply are printed as visible [PENDING ...] markers, never as invented text:
names/roll numbers, short answers (a)-(f), the contribution table, the AI statement, real screenshots, and Part E.
Edit the PLACEHOLDERS block below (or replace the paragraph) and rebuild.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent / "assignment_03_report.pdf"

# ---- PLACEHOLDERS: only the group can fill these -------------------------------------------------------
MEMBERS = "[PENDING: member 1 name, roll no.]  /  [PENDING: member 2 name, roll no.]"
REPO = "https://github.com/Sajawalkhan01/rahbar-ragops"
SHORT_ANSWERS = "[PENDING: member 2 writes short answers (a)-(f); evidence pointers are in reports/SHORT_ANSWER_FACTS.md]"
CONTRIBUTIONS = [["Member", "What they did"],
                 ["[PENDING member 1]", "[PENDING: to be confirmed by the group against `git log`]"],
                 ["[PENDING member 2]", "[PENDING: to be confirmed by the group against `git log`]"]]
AI_STATEMENT = "[PENDING: 2 to 3 lines, written by the group]"
PART_E = "[PENDING member 2: live queries (>= 40), coverage before/after, >= 6 new golden questions, coverage exit code]"
# --------------------------------------------------------------------------------------------------------

ss = getSampleStyleSheet()
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=8.3, leading=10.4, spaceAfter=3)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=12.5, spaceBefore=6, spaceAfter=3)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=9.8, spaceBefore=5, spaceAfter=2)
CELL = ParagraphStyle("c", parent=B, fontSize=7.1, leading=8.6, spaceAfter=0)
PEND = ParagraphStyle("p", parent=B, textColor=colors.HexColor("#9b1c1c"))


def P(t, st=B):
    return Paragraph(t, st)


def table(rows, widths, head=True, size=7.1):
    data = [[Paragraph(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 2.5), ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
             ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e9ef")))
    t.setStyle(TableStyle(style))
    return t


story = []
story += [P("Assignment 03: RAGOps for RAHBAR", ParagraphStyle("t", parent=ss["Title"], fontSize=17, spaceAfter=4)),
          P(f"<b>Group:</b> {MEMBERS}"), P(f"<b>Repository:</b> {REPO}"),
          P("RAHBAR (Assignment 02) is a grounded question-answering pipeline over FAST-NUCES rules, fees and annual reports. "
            "This report covers the RAGOps layer added in Assignment 03. All numbers come from files committed under "
            "<font face='Courier'>eval/results/</font>, <font face='Courier'>traces/</font> and <font face='Courier'>reports/evidence/</font>. "
            "Items marked <font color='#9b1c1c'>[PENDING]</font> have not been done yet and are not filled in with invented content.")]

# ---------------------------------------------------------------- G1
story.append(P("1. Figure 3 stages mapped to this pipeline", H1))
story.append(table([
    ["Stage", "What the pipeline does", "File", "What is missing"],
    ["Ingest", "Reads an inbox folder; skips files whose SHA-256 is unchanged (ledger); Job/CronJob on Kubernetes", "ragops/ingestion/incremental.py, cli.py", "No upload API or watcher; only folder polling by CronJob"],
    ["Verify", "Four checks per document (quality, completeness, recency, uniqueness) plus an injection advisory; failures go to quarantine with reason and action", "ragops/ingestion/verification.py, config/verification.yaml", "No semantic fact check; a reworded duplicate passes (see 6a)"],
    ["Update data lake", "Accepted files copied to datalake/&lt;doc&gt;/&lt;version&gt;; superseded versions archived; ledger records versions and history", "ragops/ingestion/state.py", "No object store or retention policy; the data volume is one PVC"],
    ["Update retrieval sources", "Embeds only changed chunks (chunk-text hash reuse), deletes stale chunks, archives by metadata; rollback; orphan audit; single-writer lock", "ragops/ingestion/incremental.py, ragops/vectorstore.py", "One embedding model; no re-embedding migration tool"],
    ["Offline testing", "Embedding, retrieval (recall@3/5, MRR, nDCG@5, noise) and end-to-end suite, run twice, one command; release gate", "ragops/evaluation/suite.py, ragops/gate.py", "Faithfulness is lexical; no LLM judge; golden set is small (34)"],
    ["Live testing", "One JSON trace per query, inspector rebuilds the prompt, metrics, guardrail log, summary", "api/app/tracing.py, ragops/tracing/", "No online A/B or user feedback capture"],
    ["Check coverage", "Embeds live queries and compares to the golden set; exit non-zero below a threshold", "ragops/evaluation/coverage.py", "[PENDING member 2] live queries not collected yet"],
], [22, 74, 44, 40]))

# ---------------------------------------------------------------- G2
story.append(P("2. The five qualities of the paper's Table 2", H1))
story.append(table([
    ["Quality", "What is measured", "Threshold", "Evidence"],
    ["Adaptability", "Chunks embedded on an unchanged / changed / new / deleted document; orphan count", "unchanged = 0 embedded; deleted = 0 orphans", "A2-incremental-demo.txt (run on real Chroma); F2-cronjob-manual-run.txt (0 embedded on unchanged input in the cluster)"],
    ["Monitorability", "Gate metrics vs baseline and absolute floors; p95 latency", "recall@5 drop &lt;= 0.02, MRR/nDCG@5 drop &lt;= 0.03, faithfulness &gt;= 0.90, citation validity &gt;= 0.95, correctness &gt;= 0.50, p95 &lt;= 2000 ms", "config/release_thresholds.yaml; F3-*.txt"],
    ["Observability", "Per-stage latency, abstention rate, cache hit rate, top-1 similarity, injections flagged", "none set (reported only)", "traces/metrics/summary.json; D3-trace-summary.txt"],
    ["Traceability", "Every answer has a trace id, context, prompt hash, collection and embedding version; inspector rebuilds the prompt and compares the hash", "hash must MATCH", "D2-trace-inspector-guardrail.txt; F6-rollout-undo.txt"],
    ["Reliability", "Suite run twice with the same seed; guardrail actions; rollback restores the previous index", "quality-metric difference between runs = 0", "suite-baseline-*.json (stochasticity block); F5/F6"],
], [22, 62, 52, 44]))

# ---------------------------------------------------------------- Results
story.append(P("3. Results", H1))
story.append(P("Part A: verification and incremental update", H2))
story.append(P("Batch A (the nine A2 documents): 601 chunks, second run on unchanged input embeds 0 chunks. Batch B (18 files with planted problems): "
               "<b>8 PASS, 10 FAIL</b> (quarantined). Failures by check: uniqueness 4 (exact copy, reformatted copy, draft near-duplicate, scholarship copy), "
               "quality 3 (empty, corrupt PDF, garbled text), completeness 3 (no metadata, truncated file, garbled text also truncated), recency 1 (stale 2023 resubmission). "
               "The reworded library-rules duplicate and the injected plagiarism note both passed verification (the injection is an advisory by policy and is removed at query time instead). "
               "In the cluster the same Batch B run embedded 26 chunks (627 in collection). Evidence: eval/results/ingestion/verification-*batchB*.md, A1-batch-b-ingest-k8s.txt."))
story.append(P("Part B: offline suite (baseline, 34 golden questions, state A uses 29, extractive generator, seed 20260301)", H2))
story.append(table([
    ["Level", "Result"],
    ["Embedding (nomic-embed-text)", "16 paraphrase pairs mean cosine 0.887 (min 0.821); 16 unrelated pairs mean 0.502 (max 0.619); gap 0.384; every paraphrase pair above every unrelated pair; deterministic (max diff 0.0); 1.72 s per chunk on CPU"],
    ["Retrieval (23 answerable/hard)", "recall@3 0.913, recall@5 0.913, MRR 0.855, nDCG@5 0.861. Noise: irrelevant docs MRR 0.833 (-0.022); typos MRR 0.826 (-0.029)"],
    ["End-to-end (29)", "answer correctness 0.609, faithfulness 1.0 (lexical, high by construction for an extractive generator), citation validity 1.0, abstention correctness 1.0, false abstention 0.174, p50/p95 38/536 ms"],
    ["Reproducibility", "Run twice: 65 metrics compared, largest quality difference 0.0; only latency and embedding time differ. The same suite on the cluster gave identical quality numbers (eval/results/k8s/)."],
], [40, 140]))
story.append(P("Part C: experiments and the release decision", H2))
story.append(table([
    ["Candidate (one change)", "recall@5", "MRR", "nDCG@5", "Answer correct.", "False abstain", "Gate", "Decision"],
    ["baseline", "0.913", "0.855", "0.861", "0.609", "0.174", "-", "-"],
    ["chunk size 400 to 200", "0.957", "0.780", "0.816", "0.609", "0.130", "FAIL (MRR -0.075, nDCG -0.045)", "<b>REJECT</b>"],
    ["top_k 5 to 3", "0.913", "0.855", "0.861", "0.609", "0.217", "PASS", "<b>RELEASE</b>"],
    ["bad: top_k 1, floor 0.90", "0.913", "0.855", "0.861", "0.391", "0.522", "FAIL (correctness)", "<b>REJECT</b>"],
], [34, 15, 13, 15, 22, 20, 40, 21]))
story.append(P("<b>Release decision.</b> top_k 3 is released: it passes every rule, and the metrics equal the baseline. Its hypothesis (less context per answer, lower cost per query) is not isolated by this suite: quality equals the baseline and no latency gain is claimed. "
               "<b>Caveat:</b> its false-abstention rate rose from 0.174 to 0.217 and the gate has no rule for that, so a worse user-facing behaviour passed. "
               "chunk 200 is rejected: better recall@5 but the right chunk ranks lower (MRR, nDCG@5 fall beyond the allowed drop). Editing the ConfigMap "
               "(max_mrr_drop 0.03 to 0.08, max_ndcg5_drop to 0.05) made the same candidate pass in the cluster with no image rebuild; that shows the gate is policy, not that the candidate improved."))
story.append(P("Part D: traces and guardrails", H2))
story.append(P("400 traces summarised (eval runs): abstention rate 0.35, cache hit rate not measured (cache bypassed in eval), retrieval p50/p95 26/462 ms, "
               "36 injection attempts flagged (26 questions, 10 retrieved-passage sentences removed from the planted note). The inspector rebuilds the prompt from the stored passages and the hash matches "
               "(D2-trace-inspector-guardrail.txt). <b>Root cause from a trace (D5):</b> "
               "<font color='#9b1c1c'>[PENDING member 2: five lines for golden question h05, trace 3f951a96...; the data is in eval/results/DRIFT-A-vs-AB.md]</font>"))
story.append(P("Part E: drift and coverage", H2))
story.append(P("Batch B ingested, suite re-run in state AB (eval/results/DRIFT-A-vs-AB.md). The five questions that need Batch B (h06-h10) enlarge the denominator, so the aggregates are not comparable; on the 23 common questions: "
               "fee questions q04 and e02 now answered from the 2027-28 fee page (intended); h02 recall falls to 0 because its golden label still names the old fee page (label to update); "
               "i01 and h03 MRR 1.0 to 0.5 and h05 abstains because the new plagiarism note competes in ranking (real degradation). "))
story.append(P(PART_E, PEND))

story.append(P("Part F: Kubernetes (minikube, namespace ragops)", H2))
story.append(table([
    ["Item", "Result (evidence file)"],
    ["Deployed", "Chroma StatefulSet, Redis, API x2, candidate API, 3 PVCs, 2 ConfigMaps, ingest Jobs, CronJob, eval Jobs (F1-cluster-state.txt)"],
    ["Ingestion", "Batch A 601 chunks in 28 min on CPU; candidate collection 726 chunks; Batch B 26 chunks; CronJob on unchanged input embeds 0 (F2-*)"],
    ["Gate in cluster", "chunk-200 Job Failed (exit 1, gate FAIL); top_k 3 Job Complete (PASS); thresholds edited in ConfigMap, same Job then Complete (F3-*, F2-threshold-*)"],
    ["Rolling update", "TOP_K 5 to 3, maxSurge 1 / maxUnavailable 0, 2/2 available, revision 2 (F4)"],
    ["Bad release and undo", "gate skipped: collection rahbar_c200, top_k 1, floor 0.90; the two-part fee/withdrawal question is refused; <i>kubectl rollout undo</i>; new trace shows collection rahbar, embedding_model_version 0a109f422b47, same index id as before the bad release (F5, F5b, F6)"],
    ["Resources", "api 77-102 MB (limit 384Mi), chroma 100-160 MB (1Gi), redis 7 MB (128Mi); no restarts or OOMKills. Job peaks not measured; metrics-server failed (F7)"],
    ["Not done / limits", "OCR packages absent from the cluster image (image built offline); the Dockerfile build did not finish on this network; no two-writer test in the cluster; eval-candidate-bad not run in the cluster"],
], [32, 148]))

# ---------------------------------------------------------------- short answers etc
story.append(P("4. Short answers (a)-(f)", H1))
story.append(P(SHORT_ANSWERS, PEND))
story.append(P("5. Contributions and AI statement", H1))
story.append(table(CONTRIBUTIONS, [40, 140]))
story.append(P(f"<b>AI statement:</b> {AI_STATEMENT}", PEND))

# ---------------------------------------------------------------- appendix
story.append(PageBreak())
story.append(P("Appendix: screenshots A-F", H1))
story.append(P("The assignment requires screenshots from the group's own terminal. <b>None are included yet.</b> The text below lists the committed, "
               "unmodified output of each command (reports/evidence/) to be screenshotted; reports/evidence/CAPTURE_CHECKLIST.md gives the exact command for each.", B))
story.append(table([
    ["Item", "Required", "Text evidence (screenshot [PENDING])"],
    ["A", "Batch B verification report; second run 0 chunks", "eval/results/ingestion/verification-*batchB*.md, A1-batch-b-ingest-k8s.txt, F2-cronjob-manual-run.txt"],
    ["B", "Evaluation summary, all three levels", "eval/results/suite-baseline-*.md"],
    ["C", "Gate failing and passing", "F3-gate-fail-chunk200-job.txt, F3-gate-pass-topk3-job.txt"],
    ["D", "One full trace; tool rebuilding the prompt", "D2-trace-inspector-guardrail.txt, traces/logs/k8s/*.jsonl"],
    ["E", "Coverage before and after", "[PENDING member 2]"],
    ["F", "get all,pvc,configmap,cronjob,job; ingest and eval Job logs; gate change after ConfigMap edit; rollout status and undo with trace",
     "F1-cluster-state.txt, F2-ingest-batch-a-job.txt, F2-threshold-change-gate-pass.txt, F4-F6"],
], [12, 70, 98]))


def footer(canvas, doc):
    canvas.setFont("Helvetica", 7)
    canvas.drawString(15 * mm, 8 * mm, "Assignment 03 RAGOps report")
    canvas.drawRightString(195 * mm, 8 * mm, f"page {doc.page}")


doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=14 * mm,
                        title="Assignment 03 RAGOps report")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
