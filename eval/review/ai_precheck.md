# AI pre-check of synthetic golden questions (NOT the human review)

Written by the AI assistant. It compares each reference answer with the text of the source file. It is **not** a review:
the human verdicts belong in `synthetic_review_sheet.jsonl` and must be entered by the person who read the source.
Use this file to know where to look and what to confirm.

Checked against the Markdown files in `eval/batch_b/` (full text read):

| ID | Reference answer vs source | Pre-check result |
| --- | --- | --- |
| n01 | Rs 20 per overdue day; unpaid fines block transcript and next-semester registration (`library-rules.md`, Renewal and Fines) | matches |
| n02 | Same edition, or current price plus Rs 500 processing charge (Lost Books) | matches |
| n03 | Semester GPA 3.50+, at least 15 credit hours, covers 50% of next semester's tuition (Merit Scholarship Eligibility) | matches |
| n04 | Seated at least ten minutes early; arrival after the first thirty minutes of a final means no entry (`examination-rules-faq.md`, Reporting Time) | matches |
| n05 | Calculator without programmable memory, pen, admit card; phone in the hall is unfair means (Items Allowed) | matches |
| n06 | Rechecking within three working days of the result; marks after rechecking are final (Result Rechecking) | matches |
| h06 | Rs. 13,500 per credit hour for BBA/BS, MBA/MS, PhD (`fee-structure-2027-28.md`, Tuition Fee) | matches |
| h07 | CGPA below 3.00: probation next semester; withdrawn after two consecutive semesters below 3.00 (Scholarship Renewal) | matches |
| h08 | Postgraduates: six books for twenty-one days (Borrowing Limits) | matches |
| h09 | Generative AI only if the instructor allows it in the course outline; disclose in a footnote (`plagiarism-and-ai-guidance.md`) | matches |
| h02 (fee half only) | After the second week the fee is 6,000 in 2027-28 (Miscellaneous Fees) | fee half matches; the deadline half comes from the handbook PDF and was **not** checked here |

**Things the reviewer should look at, not just tick:**
* **h02:** `course-withdrawal-guide.md` says withdrawal is allowed up to the end of the ninth week, while the golden answer
  says "last day of the makeup week" (2026 rules handbook). The question says "under the 2026 rules", so the handbook is the
  source, but the two documents disagree and the group should decide and say so in the report.
* **h09 / h05:** `plagiarism-and-ai-guidance.md` contains a planted instruction sentence. It is deliberate test data, not a
  review problem.

**Not pre-checked** (the source is a PDF that was not re-opened for this file): h01, h03, h04, h05, h10, and the deadline half of
h02. h05's reference answer is consistent with a handbook excerpt in trace `3f951a96...` ("Plagiarism: Deliberately
presenting work, words, ideas, theories, etc., derived ..."), but its page number (34) was not verified. The unanswerable questions u04, u05, u06
were not re-checked against the corpus (A2 recorded that the corpus has no parking, visa or swimming-pool rules).


## AI pre-check of the 12 answers in `answer_labels.jsonl` (NOT the human labels)

Read from the answer text only; I did not re-open the retrieved context, so "faithful" (is every claim in the context?) still needs
you. The extractive provider copies sentences, so claims should be in the context; the real questions are whether the answer
addresses the question and whether the sentences are mixed from the wrong year or version.

| ID | What to look at |
| --- | --- |
| q01 | Answers the question (2.00 for BS/BBA). Looks fine. |
| q02 | Contains the three-semesters rule (5.6, 3.28). Looks fine. |
| q03 | Contains Rs. 12,000 for 2026-27, **but also the 2027-28 fee (Rs. 13,500)** in the same answer: correct fact present, mixed with another year. |
| q04 | **Does not state the one-time admission fee**; only the Rs 20,000 refundable deposit. Half-answered. |
| q05 | Says fee is not refunded for a withdrawn course. Looks fine. |
| q06 | Contains "maximum of 2 courses" (6.6). Looks fine, with unrelated rules around it. |
| q07 | States CGPA 3.90 or more (Summa/Suma cum laude). Looks fine. |
| q08 | Contains the reason (lacks critical analysis). Looks fine. |
| q09 | Asks what must be **published**; the answer describes being PI/Co-PI of an externally funded project, not publications. Check against the policy text. |
| v01 | Mentions "five courses" but does not state the normal load directly. Weak. |
| v02 | 130 credit hours (1.25). Check that the retrieved chunk is from the 2023 rules, as the question says. |
| v03 | Question is about the **2023** rules, but the text carries a "Rules and Regulations 2026" page footer. Check which year the passage comes from. |

Faithfulness label is yours: true only if every claim is in the retrieved context, whether or not it answers the question.
