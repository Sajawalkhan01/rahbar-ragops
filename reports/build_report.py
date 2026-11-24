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
MEMBERS = "Muhammad Sajawal Khan (24K-3068)  /  Muhammad Abdullah (24I-3141)"
REPO = "https://github.com/Sajawalkhan01/rahbar-ragops"
SHORT_ANSWERS = [
    "<b>(a) Which Batch B check caught the most, what got through, what would catch it?</b> Uniqueness caught the most: 4 of the 10 failures (exact copy, reformatted copy, draft near-duplicate, scholarship copy); quality and completeness caught 3 each, recency 1. "
    "<i>library-rules-reworded.md</i> (same rules, different words) passed all four checks and is indexed next to the original. The injected <i>plagiarism-and-ai-guidance.md</i> also passed, because injection is only an advisory in our policy; it was handled at query time. "
    "A document-level embedding-similarity check would catch the reworded duplicate; a claim-level contradiction check would be needed for conflicting versions of one rule.",
    "<b>(b) A module metric looked fine but a higher level did not.</b> The embedding module separated paraphrase pairs (0.887) from unrelated pairs (0.502) perfectly and deterministically, yet recall@5 on hard questions was only 0.60. After Batch B the right chunk for i01 and h03 fell from rank 1 to 2 (MRR 1.0 to 0.5). "
    "The chunk-200 candidate shows it too: recall@5 rose (0.913 to 0.957) while MRR fell (0.855 to 0.780).",
    "<b>(c) Archive or delete old versions?</b> We archive. A superseded version stays as metadata (superseded=True, status=archived) with its raw file under archive/, and rollback restores it (A2-incremental-demo.txt). "
    "If the archive were deleted, rollback would be impossible and old answers and traces could not be reproduced, because the version they cite would be gone.",
    "<b>(d) Which metric do we trust least?</b> Faithfulness. It is a lexical overlap score and is 1.0 by construction with the extractive generator, since every answer is copied from the context. Answer correctness (word overlap with a reference) is also weak, and the golden set is small (34; 23 retrieval questions), so one question moves recall@5 by about 0.04.",
    "<b>(e) Which paper idea was hardest to apply, and what did we change?</b> Live testing and coverage checking, because they assume real users and we had none. The 40 live queries were drafted by hand, so the coverage result (47.5% rising to 52.5%, then 82.6% after a second round of golden questions, still below the 85% target) says more about our drafted queries than about real usage; we reported it as such. "
    "We also could not run a real LLM usefully on a CPU (0 of 6 answers accepted, LLM-SPOTCHECK.md), so we changed the suite to a deterministic extractive generator and said which metric that makes weak (faithfulness).",
    "<b>(f) Which Kubernetes object carries which responsibility?</b> Single writer: only the ingestion Job and CronJob mount the data volume read-write and set RAGOPS_ROLE=ingestor; the CronJob uses concurrencyPolicy Forbid; the API Deployment does not mount that volume. "
    "StatefulSet chroma and its PVC: vector-store persistence. ConfigMap ragops-config: the embedding model, stated once for every pod. ConfigMap release-thresholds: the gate policy. Eval Jobs: the gate (a failing gate fails the Job and stops the release). "
    "API Deployment with RollingUpdate and maxUnavailable 0: releases without downtime; rollout undo and change-cause annotations: rollback and history. PVC ragops-traces: traceability. Candidate Deployment and Service on rahbar_c200: an isolated candidate index. "
    "Limit: a two-writers-at-once test was not run in the cluster.",
]
CONTRIBUTIONS = [["Member", "What they did (from git log)"],
                 ["Sajawalkhan01", "Parts A-D code and runs (verification, quarantine, incremental ingest, evaluation suite, gate, tracing), the 18-file Batch B set, Part F (Kubernetes manifests, Jobs, rollout and rollback demos, cluster evidence), report builder; 24 commits."],
                 ["abdy879", "Part E: 40 live queries, coverage before and after, golden questions n01-n06; review sheets for the synthetic golden questions and the 12 answer labels; D5 analysis of h05; short answers; 15 commits including merges of PRs #1-#5."]]
AI_STATEMENT = ("Claude Code (Anthropic) wrote most of the code, manifests and first drafts of documents, and ran the commands; details in docs/AI-USAGE.md. "
                "The group chose the scope, ran and approved the commands, reviewed pull requests, and checked results against committed output. "
                "The live queries, review sheets and drafts of the short answers were also prepared with AI help and then edited by the group.")
PART_E = ("<b>Coverage (E1, E2, E4).</b> Live queries were compared with the golden set at cosine threshold 0.78 (nomic-embed-text, the pipeline's own embedder); the requirement is 85% covered. All live queries were drafted with AI help, not real traffic. "
          "<b>Round 1:</b> 40 live queries (34 in-domain, 6 outside the corpus). Before: 34 golden questions, 19 of 40 covered (47.5%; in-domain 50.0%), mean best similarity 0.7456. We added n01-n06 (library, scholarship, exam rules). "
          "After: 40 golden, 21 of 40 covered (<b>52.5%</b>; in-domain 55.9%), mean 0.7735. We re-ran both on 24 Nov with a freshly installed Ollama and got identical counts. "
          "<b>Round 2:</b> we added 6 live queries outside the corpus (46 live queries, 12 outside, as the brief asks) and 18 golden questions n07-n24 (12 answerable or hard on the uncovered topics, 6 must-abstain). Result: 58 golden, 38 of 46 covered (<b>82.6%</b>; in-domain 88.2%), mean 0.8519. "
          "<b>The 85% target is still not met</b> and the checker exits non-zero; 39 of 46 were needed. The 8 uncovered queries: four in-domain (AI use in a thesis, automatic scholarship renewal, fee increase over last year, research paper counts) and four outside the corpus (weather, passport, restaurant, cricket). "
          "<b>Limits:</b> the gain is partly circular (n01-n24 were written after seeing which queries were uncovered); n07-n24 are AI-drafted and not yet hand-reviewed; the queries are not real traffic. One earlier claim was wrong: missed exams do have a rule (academic rules, section 5.13, p.25), so n11 is answerable. "
          "Evidence: eval/results/COVERAGE-before-vs-after.md and coverage-repro-before/after and coverage-round2 files.")
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
    ["Check coverage", "Embeds live queries and compares to the golden set; exit non-zero below a threshold", "ragops/evaluation/coverage.py", "Coverage 47.5% to 52.5% (round 1), 82.6% after n07-n24 (round 2); still below the 85% target (Part E)"],
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
               "question h05 (plagiarism), trace 3f951a96. (1) Retrieval worked: the top three chunks are from the new plagiarism-and-ai-guidance.md, top score 0.7553, above the 0.70 floor. "
               "(2) The guardrail fired correctly (injection_sentence_removed) and replaced the planted instruction with a marker. "
               "(3) The extractive provider then answered 'The documents do not cover that question' (answered_from_context false). "
               "(4) Only one sentence reached the 0.34 overlap needed (0.50): the harmless sentence after the removed one. But the marker ends in ']' with no full stop, so the splitter merged the two, and the provider drops any sentence that contains the marker. "
               "(5) <b>Root cause: a sentence-boundary bug between guardrail and provider, not retrieval or the corpus.</b> Not fixed (a fix changes the baseline and needs a new gate run); not tested with a real LLM. Evidence: reports/evidence/D5-h05-evidence.md."))
story.append(P("<b>Hand review.</b> 10 of the 19 synthetic golden questions were checked by hand against their source files (h06-h09, n01-n06): all 10 verdict ok (eval/review/synthetic_review_sheet_reviewed.jsonl). "
               "12 answers were labelled for faithfulness by hand (eval/review/answer_labels_reviewed.jsonl): 6 faithful, 6 not faithful (q03, q04, q08, q09, v01, v03). "
               "The automatic lexical score called all 12 faithful (1.0), so <b>agreement is 6 of 12 = 0.50</b>. "
               "The low agreement is expected: the automatic score is lexical overlap with the retrieved text, while the human label asks whether the claim is supported by the cited source, so copied text from the wrong year or an unrelated rule still scores 1.0. The automatic score is too lenient: it rewards copied text even when the answer mixes years, misses part of the question, or is not supported by the cited source."))
story.append(P("Part E: drift and coverage", H2))
story.append(P("Batch B ingested, suite re-run in state AB (eval/results/DRIFT-A-vs-AB.md). The five questions that need Batch B (h06-h10) enlarge the denominator, so the aggregates are not comparable; on the 23 common questions: "
               "fee questions q04 and e02 now answered from the 2027-28 fee page (intended); h02 recall falls to 0 because its golden label still names the old fee page (label to update); "
               "i01 and h03 MRR 1.0 to 0.5 and h05 abstains because the new plagiarism note competes in ranking (real degradation). "))
story.append(P(PART_E))

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
for _a in SHORT_ANSWERS:
    story.append(P(_a))
story.append(P("5. Contributions and AI statement", H1))
story.append(table(CONTRIBUTIONS, [40, 140]))
story.append(P(f"<b>AI statement:</b> {AI_STATEMENT}"))

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
    ["E", "Coverage before and after", "eval/results/COVERAGE-before-vs-after.md; coverage command with --label before / --label after; eval/results/coverage-round2-*.md"],
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
