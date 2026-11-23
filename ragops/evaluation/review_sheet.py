"""Human review aids (assignment B: hand review of synthetic questions, and judge agreement).

    python -m ragops.evaluation.review_sheet golden            # sheet of synthetic questions to check by hand
    python -m ragops.evaluation.review_sheet answers <suite-result.json>   # sheet of answers to label by hand
    python -m ragops.evaluation.review_sheet agreement eval/review/answer_labels.jsonl   # agreement, once filled

The sheets are written with EMPTY label fields on purpose. Nothing here fills them in: a human reads the
question, the reference answer and the cited source page, and writes the verdict. `agreement` then compares the
human labels with the automatic faithfulness score (support >= 0.55 counts as 'faithful').
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eval" / "review"


def golden_sheet() -> Path:
    rows = [json.loads(x) for x in (ROOT / "eval" / "golden.jsonl").read_text(encoding="utf-8").splitlines()]
    sheet = [{"id": r["id"], "question": r["question"], "reference_answer": r["answer"],
              "ground_truth": r["relevant"], "check_these": ["question is clear and answerable (or truly unanswerable)",
                                                             "reference answer is correct per the source",
                                                             "source / page / section is right"],
              "reviewer": "", "verdict": "", "notes": ""}
             for r in rows if r["author"] == "synthetic"]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "synthetic_review_sheet.jsonl"
    path.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in sheet) + "\n", encoding="utf-8")
    return path


def answers_sheet(result_file: str, n: int = 12) -> Path:
    r = json.loads(Path(result_file).read_text(encoding="utf-8"))
    per_q = [q for q in r["runs"][0]["generation"]["per_question"] if q["answered"]]
    step = max(1, len(per_q) // n)
    picked = per_q[::step][:n]
    sheet = [{"id": q["id"], "question": q["question"], "answer": q["answer"],
              "auto_faithfulness": q["faithfulness"], "trace_id": q["trace_id"],
              "human_faithful": None, "reviewer": "", "notes": ""} for q in picked]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "answer_labels.jsonl"
    path.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in sheet) + "\n", encoding="utf-8")
    return path


def agreement(path: str, threshold: float = 0.55) -> dict[str, object]:
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    done = [r for r in rows if r["human_faithful"] is not None]
    if not done:
        return {"labelled": 0, "note": "no human labels yet"}
    agree = sum(bool(r["human_faithful"]) == (r["auto_faithfulness"] >= threshold) for r in done)
    return {"labelled": len(done), "agree": agree, "agreement": round(agree / len(done), 3),
            "disagreements": [r["id"] for r in done
                              if bool(r["human_faithful"]) != (r["auto_faithfulness"] >= threshold)]}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("golden", "answers", "agreement"):
        print(__doc__)
        return 2
    if sys.argv[1] == "golden":
        print(golden_sheet())
    elif sys.argv[1] == "answers":
        print(answers_sheet(sys.argv[2]))
    else:
        print(json.dumps(agreement(sys.argv[2]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
