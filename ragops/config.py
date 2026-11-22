"""Paths and YAML configuration. Everything that differs between a laptop and the cluster is
an environment variable, so one image runs both (A2's rule: nothing environment-specific baked in).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(os.environ.get("RAGOPS_ROOT", Path(__file__).resolve().parents[1]))


def config_dir() -> Path:
    return Path(os.environ.get("RAGOPS_CONFIG_DIR", ROOT / "config"))


def load_yaml(name: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read config/<name> (or an absolute/relative path). `overrides` is a nested dict merged on top."""
    path = Path(name)
    if not path.is_absolute() and not path.exists():
        path = config_dir() / name
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return deep_merge(data, overrides or {})


def deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass(frozen=True)
class Paths:
    """Where the RAGOps layer keeps its state. On Kubernetes these are PVC mount points."""

    data: Path          # RAGOPS_DATA_DIR: the data PVC (/data)
    inbox: Path         # incoming batches (read, quarantined files are moved out of here)
    datalake: Path      # accepted raw documents, by doc id and version
    quarantine: Path
    archive: Path       # superseded / deleted document versions (kept for rollback)
    state: Path         # ledger.json, extraction cache, writer lock
    reports: Path       # verification and ingestion reports per run
    results: Path       # eval/results (a separate PVC on the cluster)
    traces: Path        # JSONL traces (a separate PVC on the cluster)

    def ensure(self) -> Paths:
        for p in (self.inbox, self.datalake, self.quarantine, self.archive, self.state,
                  self.reports, self.results, self.traces):
            p.mkdir(parents=True, exist_ok=True)
        return self


def get_paths() -> Paths:
    data = Path(os.environ.get("RAGOPS_DATA_DIR", ROOT / "data"))
    return Paths(
        data=data,
        inbox=Path(os.environ.get("RAGOPS_INBOX_DIR", data / "inbox")),
        datalake=data / "datalake",
        quarantine=data / "quarantine",
        archive=data / "archive",
        state=data / "state",
        reports=data / "reports",
        results=Path(os.environ.get("RAGOPS_RESULTS_DIR", ROOT / "eval" / "results")),
        traces=Path(os.environ.get("RAGOPS_TRACE_DIR", ROOT / "traces" / "logs")),
    )
