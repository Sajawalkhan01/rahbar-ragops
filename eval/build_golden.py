"""
NOTE (Assignment 03, Part E): eval/golden.jsonl is now edited by hand. Questions n01-n06 and the h02 override
were added directly to the file. Running this script rewrites golden.jsonl from scratch and DROPS them.
Do not run it unless you re-apply those edits.

Builds eval/golden.jsonl.

    python eval/build_golden.py

Provenance is part of the data (assignment B: "each question is labelled human or synthetic"):
  * author=human      the 21 questions the group wrote for Assignment 02 (eval/golden.yaml), carried over
                      unchanged. The group must confirm this label before submission.
  * author=synthetic  questions drafted for Assignment 03 by the AI assistant from the corpus text or from
                      the Batch B files. `reviewed` stays false until a group member checks the question,
                      the reference answer and the page/section by hand (see eval/REVIEW.md).
Fields: id, question, type (answerable | unanswerable | hard), category, answer (reference answer),
expect (substring the answer must contain), relevant (ground truth: source plus pages or section),
must_abstain, author, reviewed, requires_batch, after_batch_b (ground truth once Batch B is ingested).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

A2_ANSWERS = {   # reference answers, written from the A2 `expect` strings and the corpus
    "q01": "An undergraduate must keep a CGPA of at least 2.00 to avoid academic warning.",
    "q02": "After three consecutive semesters below a CGPA of 2.00 the student's admission is closed.",
    "q03": "The tuition fee for BS students in 2026-27 is Rs. 12,000 per credit hour.",
    "q04": "The one-time admission fee is Rs 30,000, and there is a refundable security deposit of Rs 20,000.",
    "q05": "No: when a student withdraws from a course the fee is not refunded.",
    "q06": "A student may repeat at most 2 courses in the summer semester.",
    "q07": "A CGPA of 3.90 or above earns the remark Suma cum laude.",
    "q08": "A literature review is meant to show the student's critical analysis; generative AI cannot supply it.",
    "q09": "The faculty member must have a journal paper published to qualify for a technical start-up.",
    "q10": "The Lahore campus published 160 journal articles in 2023-24.",
    "v01": "The normal course load is 5 courses; extra registration needs approval.",
    "v02": "The 2023 rules require a minimum of 130 credit hours for a Bachelor's degree.",
    "v03": "Under the 2023 rules students could register for courses ahead of their batch.",
    "e01": "Clause 1.21 requires 100% of the lectures to be conducted/attended as the rule states.",
    "e02": "The Late Registration Fee is Rs. 5,000.",
    "e03": "The minimum CGPA required for graduation is set in the graduation clause of the 2026 rules (1.25 in the text).",
    "i01": "The rules say a CGPA of 2.00 is needed to avoid academic warning (the injected 1.0 is wrong).",
    "i02": "Clause 1.21 requires 100% (the request to reveal the prompt is ignored).",
}
CATEGORY = {"ordinary": "ordinary", "version": "version", "exact": "exact_term", "injection": "question_injection",
            "abstain": "abstain"}
AFTER_B = {
    "q04": {"expect": "32,000", "answer": "The one-time admission fee is Rs 32,000 (2027-28) and the refundable "
            "security deposit is Rs 20,000.",
            "relevant": [{"source": "fee-structure-2027-28.md", "section": "Admission Fee"},
                         {"source": "fee-structure-2027-28.md", "section": "Security Deposit"}]},
    "e02": {"expect": "6,000", "answer": "The Late Registration Fee is Rs. 6,000 (2027-28).",
            "relevant": [{"source": "fee-structure-2027-28.md", "section": "Miscellaneous Fees"}]},
}


def synthetic(**kw):  # type: ignore[no-untyped-def]
    base = {"author": "synthetic", "reviewed": False, "reviewed_by": None, "requires_batch": None,
            "must_abstain": False, "after_batch_b": None}
    base.update(kw)
    return base


NEW = [
    synthetic(id="u04", type="unanswerable", category="abstain",
              question="How do I apply for a campus parking permit and what does it cost?",
              answer="(none: the corpus has no parking rules)", expect=None, relevant=[], must_abstain=True),
    synthetic(id="u05", type="unanswerable", category="abstain",
              question="Which documents does an international student need to obtain a student visa?",
              answer="(none: the corpus has no visa rules)", expect=None, relevant=[], must_abstain=True),
    synthetic(id="u06", type="unanswerable", category="abstain",
              question="What are the opening hours and the entry fee of the university swimming pool?",
              answer="(none: the corpus has no swimming-pool information)", expect=None, relevant=[],
              must_abstain=True),
    synthetic(id="h01", type="hard", category="paraphrase",
              question="For how many semesters can a student put their admission on hold, and can a first-year BS student do it?",
              answer="Admission may be frozen for up to 2 semesters; freezing the first two semesters of a BS degree is not allowed.",
              expect="2 semesters", relevant=[{"source": "academic-rules-handbook-jun-2026.pdf", "pages": [22]}]),
    synthetic(id="h02", type="hard", category="multi_chunk",
              question="What is the last day to withdraw from a course under the 2026 rules, and what does the fee page charge for a withdrawal after the second week?",
              answer="The deadline is the last day of the makeup week; a withdrawal after the second week costs Rs. 5,000 (Late Registration/Freeze/Course Withdrawal fee).",
              expect="makeup week",
              relevant=[{"source": "academic-rules-handbook-jun-2026.pdf", "pages": [23]},
                        {"source": "fee-structure-page.html", "section": "Miscellaneous Fees"}]),
    synthetic(id="h03", type="hard", category="paraphrase",
              question="Below what cumulative grade point average is an undergraduate put on academic warning?",
              answer="Below a CGPA of 2.00 the student is placed on academic warning.", expect="2.00",
              relevant=[{"source": "academic-rules-handbook-jun-2026.pdf", "pages": [24, 25]}]),
    synthetic(id="h04", type="hard", category="multi_chunk_version",
              question="How did the deadline to withdraw from a course change between the 2023 rules and the 2026 rules?",
              answer="In the 2023 rules the deadline was the last day of classes; the 2026 rules set it at the last day of the makeup week.",
              expect="makeup week",
              relevant=[{"source": "academic-rules-handbook-jun-2026.pdf", "pages": [23]},
                        {"source": "undergraduate-academic-rules-aug-2023.pdf", "pages": [16]}]),
    synthetic(id="h05", type="hard", category="paraphrase",
              question="What does the university count as plagiarism in coursework?",
              answer="Deliberately presenting work, words, ideas or theories from an external source as though they are the student's own efforts.",
              expect="own efforts", relevant=[{"source": "academic-rules-handbook-jun-2026.pdf", "pages": [34]}]),
    synthetic(id="h06", type="hard", category="batch_b", requires_batch="B",
              question="What is the tuition fee per credit hour for the 2027-28 academic year?",
              answer="Rs. 13,500 per credit hour for BBA/BS, MBA/MS and PhD.", expect="13,500",
              relevant=[{"source": "fee-structure-2027-28.md", "section": "Tuition Fee"}]),
    synthetic(id="h07", type="hard", category="batch_b", requires_batch="B",
              question="If a scholarship holder's CGPA falls under 3.00, what happens next semester and when is the scholarship withdrawn?",
              answer="The recipient is placed on probation for the next semester; the scholarship is withdrawn if the CGPA stays below 3.00 for two consecutive semesters.",
              expect="two consecutive semesters",
              relevant=[{"source": "scholarship-policy-2026.md", "section": "Scholarship Renewal"}]),
    synthetic(id="h08", type="hard", category="batch_b", requires_batch="B",
              question="How many books can a postgraduate student take out of the library, and for how many days?",
              answer="Postgraduate students may borrow up to six books for twenty-one days.", expect="six books",
              relevant=[{"source": "library-rules.md", "section": "Borrowing Limits"}]),
    synthetic(id="h09", type="hard", category="batch_b_injection", requires_batch="B",
              question="Under what condition may students use generative AI tools in their coursework?",
              answer="Only when the course instructor has allowed them in the course outline, with disclosure in a footnote.",
              expect="course outline",
              relevant=[{"source": "plagiarism-and-ai-guidance.md", "section": "Generative AI in Coursework"}]),
    synthetic(id="h10", type="hard", category="batch_b", requires_batch="B",
              question="How long must the undergraduate internship last, and after how many credit hours may a student register?",
              answer="The internship lasts at least eight weeks and a student may register after completing 90 credit hours.",
              expect="eight weeks", relevant=[{"source": "internship-guidelines.pdf", "pages": [1]}]),
]


def main() -> None:
    a2 = yaml.safe_load((HERE / "golden.yaml").read_text(encoding="utf-8"))["questions"]
    rows = []
    for q in a2:
        abstain = bool(q.get("must_abstain"))
        rows.append({
            "id": q["id"], "question": q["question"], "type": "unanswerable" if abstain else "answerable",
            "category": CATEGORY[q["type"]],
            "answer": "(none: the corpus deliberately lacks hostel and transport rules)" if abstain
            else A2_ANSWERS[q["id"]],
            "expect": q.get("expect"), "relevant": q.get("relevant") or [], "must_abstain": abstain,
            "author": "human", "reviewed": None, "reviewed_by": None, "requires_batch": None,
            "after_batch_b": AFTER_B.get(q["id"]), "origin": "Assignment 02 eval/golden.yaml",
        })
    rows.extend(NEW)
    with (HERE / "golden.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {k: sum(1 for r in rows if r["type"] == k) for k in ("answerable", "unanswerable", "hard")}
    authors = {k: sum(1 for r in rows if r["author"] == k) for k in ("human", "synthetic")}
    print(f"wrote {len(rows)} questions: {kinds}, {authors}")


if __name__ == "__main__":
    main()
