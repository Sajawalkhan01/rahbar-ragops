"""A read-only copy of a Chroma collection held in memory, plus extra chunks.

Used by the retrieval noise test (assignment B, component level): the live collection is only READ,
irrelevant documents are added to a private in-memory copy, and A2's own ChromaRetriever runs on that
copy unchanged. This keeps the "only the ingestion Job writes to the vector store" rule intact.
Implements just the Chroma calls the retriever makes: get, query, count, metadata.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class MemoryCollection:
    def __init__(self, name: str, metadata: dict[str, Any]) -> None:
        self.name, self.metadata = name, dict(metadata)
        self.ids: list[str] = []
        self.texts: list[str] = []
        self.metas: list[dict[str, Any]] = []
        self._vecs: list[np.ndarray] = []
        self._matrix: np.ndarray | None = None

    def add(self, chunk_id: str, text: str, meta: dict[str, Any], vec: list[float]) -> None:
        self.ids.append(chunk_id)
        self.texts.append(text)
        self.metas.append(dict(meta))
        v = np.asarray(vec, dtype=np.float32)
        self._vecs.append(v)
        self._matrix = None

    def count(self) -> int:
        return len(self.ids)

    def _mat(self) -> np.ndarray:
        if self._matrix is None:
            m = np.vstack(self._vecs)
            self._matrix = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)
        return self._matrix

    def get(self, ids: list[str] | None = None, limit: int | None = None, offset: int = 0,
            include: list[str] | None = None, **_: Any) -> dict[str, Any]:
        index = {c: i for i, c in enumerate(self.ids)}
        rows = [index[c] for c in ids if c in index] if ids is not None else list(range(len(self.ids)))
        rows = rows[offset : offset + limit] if limit is not None else rows[offset:]
        inc = include or []
        out: dict[str, Any] = {"ids": [self.ids[i] for i in rows]}
        if "documents" in inc:
            out["documents"] = [self.texts[i] for i in rows]
        if "metadatas" in inc:
            out["metadatas"] = [self.metas[i] for i in rows]
        if "embeddings" in inc:
            out["embeddings"] = [self._vecs[i].tolist() for i in rows]
        return out

    def query(self, query_embeddings: list[list[float]], n_results: int, where: dict[str, Any] | None = None,
              include: list[str] | None = None) -> dict[str, Any]:
        q = np.asarray(query_embeddings[0], dtype=np.float32)
        q = q / (np.linalg.norm(q) or 1.0)
        sims = self._mat() @ q
        order = np.argsort(-sims)
        keep: list[int] = []
        for i in order:
            if where and any(self.metas[i].get(k) != v for k, v in where.items()):
                continue
            keep.append(int(i))
            if len(keep) >= n_results:
                break
        return {"ids": [[self.ids[i] for i in keep]], "distances": [[float(1.0 - sims[i]) for i in keep]]}


class MemoryClient:
    def __init__(self) -> None:
        self.collections: dict[str, MemoryCollection] = {}

    def get_collection(self, name: str) -> MemoryCollection:
        return self.collections[name]

    @classmethod
    def copy_of(cls, source: Any, name: str) -> tuple[MemoryClient, MemoryCollection]:
        """Read every chunk (text, metadata, vector) of `source` into memory."""
        client = cls()
        coll = MemoryCollection(name, dict(source.metadata or {}))
        offset = 0
        while True:
            page = source.get(limit=300, offset=offset, include=["documents", "metadatas", "embeddings"])
            if not page["ids"]:
                break
            for i, c in enumerate(page["ids"]):
                coll.add(c, page["documents"][i], page["metadatas"][i], page["embeddings"][i])
            offset += len(page["ids"])
        client.collections[name] = coll
        return client, coll
