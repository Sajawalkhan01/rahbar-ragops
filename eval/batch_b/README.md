# Batch B: planted problems

Fifteen new documents ingested after Batch A (the nine A2 documents). The content is written for this
assignment in the domain of the RAHBAR corpus (university rules, fees, examinations); it is **synthetic**
and is not a FAST-NUCES publication. `build_batch_b.py` builds the files that cannot be typed (PDFs, a
garbled file, a truncated file).

| File | Planted problem | Expected check |
| --- | --- | --- |
| scholarship-policy-2026.md | none (a new good document) | all PASS |
| scholarship-policy-2026-copy.md | exact duplicate (byte-identical) | uniqueness (file hash) |
| library-rules.md | none | all PASS |
| library-rules-copy.md | exact duplicate (byte-identical) | uniqueness (file hash) |
| library-rules-reformatted.md | same text, different bytes | uniqueness (text hash) |
| library-rules-reworded.md | paraphrased copy (same facts, different words) | tests the limit of near-duplicate detection |
| examination-rules-faq.md | none | all PASS |
| examination-rules-faq-draft.md | near-duplicate (two words changed) | uniqueness (embedding similarity) |
| course-withdrawal-guide.md | none | all PASS |
| internship-guidelines.pdf | none (valid 2-page PDF, metadata in a sidecar) | all PASS |
| corrupt-timetable.pdf | file cut at 55% (no xref, no EOF) | quality (extraction failed) |
| exam-schedule-truncated.md | text ends mid-sentence | completeness (truncated) |
| no-metadata-notice.md | no title, source, date or version | completeness (metadata) |
| scan-notice-garbled.txt | bad-OCR symbol soup | quality (garbled) |
| empty-notice.md | metadata but no body | quality (empty) |
| academic-rules-2023-resubmission.md | stale re-upload of a superseded version | recency |
| fee-structure-2027-28.md | newer version of the A2 fee page (family `fee-structure`) | recency: supersedes the 2026-27 page |
| plagiarism-and-ai-guidance.md | an injected instruction inside a normal paragraph | advisory scan + query-time rail |
