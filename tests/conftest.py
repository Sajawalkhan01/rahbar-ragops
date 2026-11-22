"""Test setup: put the A2 packages (indexer/pipeline, api/app) and ragops on the path, and give
every test a private data directory and the ingestor role."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "indexer", ROOT / "api", ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RAGOPS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("RAGOPS_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("RAGOPS_TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("RAGOPS_ROLE", "ingestor")
    return tmp_path / "data"
