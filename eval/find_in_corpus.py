"""Helper for writing golden questions: find which document and page mention a phrase.

    python eval/find_in_corpus.py "withdraw" "grade F" --context 120
Reads the A2 extraction cache (corpus/raw/_extracted/*.json), so it needs no model and no network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phrases", nargs="+")
    ap.add_argument("--context", type=int, default=100)
    ap.add_argument("--max", type=int, default=6)
    ap.add_argument("--dir", default=str(ROOT / "corpus" / "raw" / "_extracted"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    for phrase in args.phrases:
        print(f"=== {phrase!r}")
        shown = 0
        for path in sorted(Path(args.dir).glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            for page in doc["pages"]:
                for m in re.finditer(phrase, page["text"], re.I):
                    if shown >= args.max:
                        break
                    a, b = max(0, m.start() - args.context), m.end() + args.context
                    snippet = " ".join(page["text"][a:b].split())
                    print(f"  {doc['source']} p{page['page']}: ...{snippet}...")
                    shown += 1
        if not shown:
            print("  (no match)")


if __name__ == "__main__":
    main()
