#!/usr/bin/env python3
"""Release gate CLI (C2). See ragops/gate.py for the rules.

    python experiments/release_gate.py --baseline B.json --candidate C.json [--thresholds FILE]
Exit code 0 = PASS, 1 = FAIL, 2 = a result file is missing or unreadable.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "indexer", ROOT / "api"):
    sys.path.insert(0, str(p))

from ragops.config import load_yaml  # noqa: E402
from ragops.gate import apply_gate, load, print_report  # noqa: E402


def newest(pattern: str) -> str:
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"no result file matches {pattern!r}")
    return files[-1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--thresholds", default="release_thresholds.yaml")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        baseline, candidate = load(newest(args.baseline)), load(newest(args.candidate))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read result file: {exc}", file=sys.stderr)
        return 2
    report = apply_gate(baseline, candidate, load_yaml(args.thresholds))
    print_report(report)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
