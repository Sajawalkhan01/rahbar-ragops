"""Builds the Batch B files that cannot be typed by hand (PDFs, a garbled file, a truncated file).

    python eval/batch_b/build_batch_b.py

Deterministic (fixed seed), so the files are reproducible. The hand-written Markdown documents
sit next to this script. The full list of planted problems is in eval/batch_b/README.md.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "indexer" / "tests"))
from pdfmaker import text_pdf  # noqa: E402  (A2's test helper builds valid PDFs)

INTERNSHIP = [
    ["Internship Guidelines for Undergraduate Students", "",
     "A student may register for the internship course after completing 90 credit hours.",
     "The internship must last at least eight weeks and must be completed in a single organisation.",
     "The student must find a workplace supervisor who will sign the weekly attendance sheet.",
     "The department assigns a faculty supervisor to every internship within one week of registration.",
     "Students working in a family business are not allowed to use it for the internship course.",
     "The internship is graded as Pass or Fail and does not change the CGPA of the student."],
    ["Internship Report and Assessment", "",
     "At the end of the internship the student submits a report of at least twenty pages.",
     "The report must describe the tasks performed, the skills learned and the supervisor feedback.",
     "The faculty supervisor evaluates the report and conducts a viva of fifteen minutes.",
     "A student who fails the internship may repeat it only in the next semester.",
     "The workplace supervisor submits a confidential evaluation form directly to the department."],
]
TIMETABLE = [
    [f"Mid-term timetable, week {w}: course CS{3000 + 10 * w + i} is scheduled on day {i + 1} in room "
     f"R-{100 + 7 * i + w} from {8 + i}:00 to {9 + i}:30. Students must carry the admit card."
     for i in range(12)]
    for w in range(1, 4)
]
TRUNCATED_MD = """---
title: Final Examination Schedule - Fall 2026
source: https://nu.edu.pk/Student/ExamSchedule
date: 2026-11-20
doc_version: 2026-11
---

# Final Examination Schedule

## General Instructions

The final examinations for the Fall 2026 semester start on the second Monday of December.
Each paper is of three hours duration. Students must collect their admit card from the
department office at least two days before the first paper.

## Schedule of Papers

The morning session starts at nine o'clock and the afternoon session starts at two o'clock. The
papers of the first year courses are held in the main block, and the papers of the senior courses
are held in the new academic block. A student who has a clash between two papers must report to the
examination office before the end of the week so that the clash can be resolved by arranging a
"""


def main() -> None:
    text_pdf(HERE / "internship-guidelines.pdf", INTERNSHIP)
    (HERE / "internship-guidelines.pdf.meta.json").write_text(json.dumps({
        "title": "Internship Guidelines for Undergraduate Students",
        "source": "https://nu.edu.pk/Student/Internship", "date": "2026-06-15",
        "doc_version": "2026-06", "pages": 2}, indent=1), encoding="utf-8")

    # A longer PDF cut in the middle of the file: no xref table, no %%EOF (an interrupted upload).
    full = HERE / "_timetable_full.pdf"
    text_pdf(full, TIMETABLE)
    data = full.read_bytes()
    (HERE / "corrupt-timetable.pdf").write_bytes(data[: int(len(data) * 0.55)])
    full.unlink()
    (HERE / "corrupt-timetable.pdf.meta.json").write_text(json.dumps({
        "title": "Mid-term Timetable", "source": "https://nu.edu.pk/Student/Timetable",
        "date": "2026-10-01", "doc_version": "2026-10", "pages": 3}, indent=1), encoding="utf-8")

    (HERE / "exam-schedule-truncated.md").write_text(TRUNCATED_MD, encoding="utf-8")

    rng = random.Random(7)
    alphabet = "bcdfghjklmnpqrstvwxz#@%$^&*~|<>[]{}\\/�"
    garbled = " ".join("".join(rng.choice(alphabet) for _ in range(rng.randint(4, 11))) for _ in range(160))
    (HERE / "scan-notice-garbled.txt").write_text(
        "---\ntitle: Scanned Notice (bad OCR)\nsource: https://nu.edu.pk/Notices\ndate: 2026-10-05\n"
        "doc_version: 2026-10\n---\n" + garbled + "\n", encoding="utf-8")

    (HERE / "empty-notice.md").write_text(
        "---\ntitle: Notice of Campus Closure\nsource: https://nu.edu.pk/Notices\ndate: 2026-10-12\n"
        "doc_version: 2026-10\n---\n\n", encoding="utf-8")


if __name__ == "__main__":
    main()
