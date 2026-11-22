"""In-memory stand-in for the parts of the Chroma client that the RAGOps layer uses.
Nothing here touches the network. Supports equality `where` filters on a single key."""

from __future__ import annotations

import copy
import hashlib
import math
import re
from typing import Any

DIM = 64


def vector_for(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeCollection:
    def __init__(self, name: str, metadata: dict[str, Any]) -> None:
        self.name, self.metadata = name, dict(metadata)
        self.rows: dict[str, dict[str, Any]] = {}

    def count(self) -> int:
        return len(self.rows)

    def _match(self, row: dict[str, Any], where: dict[str, Any] | None) -> bool:
        return not where or all(row["metadata"].get(k) == v for k, v in where.items())

    def get(self, ids: list[str] | None = None, where: dict[str, Any] | None = None,
            limit: int | None = None, offset: int = 0, include: list[str] | None = None) -> dict[str, Any]:
        keys = [k for k in (ids if ids is not None else list(self.rows))
                if k in self.rows and self._match(self.rows[k], where)]
        keys = keys[offset : offset + limit] if limit is not None else keys[offset:]
        out: dict[str, Any] = {"ids": keys}
        inc = include or []
        if "documents" in inc:
            out["documents"] = [self.rows[k]["text"] for k in keys]
        if "metadatas" in inc:
            out["metadatas"] = [copy.deepcopy(self.rows[k]["metadata"]) for k in keys]
        if "embeddings" in inc:
            out["embeddings"] = [list(self.rows[k]["vector"]) for k in keys]
        return out

    def upsert(self, ids, documents, embeddings, metadatas) -> None:  # type: ignore[no-untyped-def]
        for i, d, e, m in zip(ids, documents, embeddings, metadatas):
            self.rows[i] = {"text": d, "vector": list(e), "metadata": dict(m)}

    def update(self, ids, metadatas=None, **_: Any) -> None:  # type: ignore[no-untyped-def]
        for i, m in zip(ids, metadatas or []):
            self.rows[i]["metadata"] = dict(m)

    def delete(self, ids: list[str] | None = None, where: dict[str, Any] | None = None) -> None:
        for k in [k for k in list(self.rows) if (ids is None or k in ids) and self._match(self.rows[k], where)]:
            del self.rows[k]

    def query(self, query_embeddings, n_results, where=None, include=None):  # type: ignore[no-untyped-def]
        q = query_embeddings[0]
        scored = []
        for cid, row in self.rows.items():
            if not self._match(row, where):
                continue
            v = row["vector"]
            cos = sum(a * b for a, b in zip(v, q)) / ((math.sqrt(sum(a * a for a in v)) *
                                                       math.sqrt(sum(b * b for b in q))) or 1.0)
            scored.append((1.0 - cos, cid))
        scored.sort()
        top = scored[:n_results]
        return {"ids": [[c for _, c in top]], "distances": [[d for d, _ in top]]}

    def modify(self, metadata: dict[str, Any]) -> None:
        self.metadata = {**{"hnsw:space": "cosine"}, **metadata}


class FakeClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def get_collection(self, name: str) -> FakeCollection:
        if name not in self.collections:
            raise ValueError(f"collection {name} does not exist")
        return self.collections[name]

    def create_collection(self, name: str, metadata: dict[str, Any] | None = None) -> FakeCollection:
        self.collections[name] = FakeCollection(name, metadata or {})
        return self.collections[name]

    def delete_collection(self, name: str) -> None:
        self.collections.pop(name, None)
