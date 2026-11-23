# Part E: coverage before vs after adding golden questions

Similarity threshold 0.78, required share 85% (`config/evaluation.yaml`). 40 live queries.
Raw results: `coverage-before-new-golden-20261123T193716Z.*` and `coverage-after-new-golden-20261123T194446Z.*`.

| | Before | After |
| --- | --- | --- |
| Golden questions | 34 | 40 (new: n01-n06) |
| Covered live queries | 19 of 40 (47.5%) | 21 of 40 (52.5%) |
| In-domain queries only | 50.0% | 55.9% |
| Mean best similarity | 0.7456 | 0.7735 |
| 10th percentile similarity | 0.6039 | 0.6413 |
| Meets the 85% requirement | no | **no** |

## What changed, query by query (only queries whose score moved)

| Live query | Before | After | Closest new question | Covered now |
| --- | --- | --- | --- | --- |
| l08 fine for a late library book | 0.643 | 0.902 | n01 | yes |
| l28 penalty for losing a library book | 0.605 | 0.837 | n02 | yes |
| l10 who is eligible for a merit scholarship | 0.619 | 0.764 | n03 | no (just below 0.78) |
| l31 how are exam papers rechecked | 0.597 | 0.769 | n06 | no (just below 0.78) |
| l32 when must I reach the exam hall | 0.613 | 0.755 | n04 | no |
| l14 can I bring a calculator to the exam | 0.599 | 0.709 | n04 | no |
| l15 what if I miss an exam because I was sick | 0.592 | 0.645 | n04 | no (the exam FAQ has no rule on this) |

## Reading the result honestly

* **The six new questions raised coverage from 47.5% to 52.5%. The 85% requirement is still not met.** Two queries
  became covered (the library ones). Five more moved closer but stay under the 0.78 threshold.
* **The improvement is partly circular.** n01-n06 were written after looking at which live queries were uncovered, so
  the gain shows that the coverage check and the "fill the gap" loop work. It does not show that real students are
  now better represented.
* **The live queries are not real traffic.** They were drafted by the AI assistant; the `status` field in
  `eval/live_queries/live_queries.jsonl` says whether a group member has reviewed each one. The percentage depends
  entirely on which queries are kept.
* **Some uncovered queries will never be covered by answerable questions**: the off-topic ones (wifi password, cafeteria
  menu, bus time) and the injection attempt. Whether they should be covered by `unanswerable` golden questions is a group decision.
* **Topics still uncovered** (from the "after" run): internship duration, ChatGPT use in assignments, repeating a
  course, admission freeze, distinction/medal CGPA, scholarship cancellation and renewal, last year's fee change,
  research paper counts, missed exams.
* **Next step if the 85% target matters:** add golden questions for those topics. Each needs an answer taken from the
  documents; a topic with no document (for example missed exams) should become an `unanswerable` question instead.
