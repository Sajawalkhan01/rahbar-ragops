"""Chroma access with a single-writer rule (paper 4.2.4, assignment F2/F6).

Reads (API, evaluation) use `get_reader()`. Writes go through `writer()`, which
  1. refuses to run unless RAGOPS_ROLE=ingestor (the ingestion Job/CronJob sets it), and
  2. takes an exclusive lock file on the state volume, so two ingestion runs cannot overlap
     even if someone starts a second Job by hand.
On Kubernetes the lock sits on the ReadWriteOnce data PVC, the CronJob has concurrencyPolicy
Forbid, and the API/evaluation Pods are not given RAGOPS_ROLE=ingestor (see k8s/README.md).
"""

from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any


class WriterNotAllowed(RuntimeError):
    pass


class WriterBusy(RuntimeError):
    pass


def chroma_endpoint() -> tuple[str, int]:
    return os.environ.get("CHROMA_HOST", "localhost"), int(os.environ.get("CHROMA_PORT", 8000))


def get_reader() -> Any:
    import chromadb
    from chromadb.config import Settings

    host, port = chroma_endpoint()
    return chromadb.HttpClient(host=host, port=port, settings=Settings(anonymized_telemetry=False))


@contextlib.contextmanager
def writer(lock_dir: Path, wait_seconds: float = 0.0) -> Iterator[Any]:
    """Yield a Chroma client that may write. Raises WriterNotAllowed / WriterBusy otherwise."""
    if os.environ.get("RAGOPS_ROLE") != "ingestor":
        raise WriterNotAllowed("only the ingestion Job may write to the vector store "
                               "(set RAGOPS_ROLE=ingestor)")
    import fcntl

    lock_dir.mkdir(parents=True, exist_ok=True)
    handle = open(lock_dir / "writer.lock", "w")  # noqa: SIM115 - held for the whole context
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.monotonic() >= deadline:
                handle.close()
                raise WriterBusy("another ingestion run holds the writer lock") from None
            time.sleep(0.5)
    try:
        handle.write(f"pid={os.getpid()} host={os.environ.get('HOSTNAME', '-')}\n")
        handle.flush()
        yield get_reader()
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()
