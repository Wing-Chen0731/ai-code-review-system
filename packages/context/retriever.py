"""Small local retrievers with an interface that can later back onto pgvector."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Iterable

from .chunker import CodeChunk
from .embedder import DeterministicEmbedder


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]+|[\u4e00-\u9fff]+", text.lower()))


def _candidate(item: dict, score: float) -> dict:
    chunk = item["chunk"]
    return {"id": chunk.chunk_id, "file_path": chunk.file_path, "content": chunk.content,
            "start_line": chunk.start_line, "end_line": chunk.end_line,
            "symbol_name": chunk.symbol_name, "score": round(score, 6)}


class KeywordRetriever:
    def __init__(self):
        self._items: list[dict] = []

    def index(self, items: Iterable[dict]) -> None:
        self._items.extend(items)

    async def retrieve(self, query: str, top_k: int = 10, **_: object) -> list[dict]:
        query_terms = _tokens(query)
        scored = []
        for item in self._items:
            terms = _tokens(item["chunk"].content)
            score = len(query_terms & terms) / max(1, len(query_terms))
            if score > 0:
                scored.append(_candidate(item, score))
        return sorted(scored, key=lambda value: (-value["score"], value["id"]))[:top_k]


class VectorStore:
    def __init__(self):
        self._items: dict[str, dict] = {}

    def upsert(self, items: Iterable[dict]) -> None:
        for item in items:
            self._items[item["chunk"].chunk_id] = item

    def delete_by_file(self, file_path: str) -> None:
        self._items = {key: value for key, value in self._items.items() if value["chunk"].file_path != file_path}

    def search(self, embedding: list[float], top_k: int = 10) -> list[dict]:
        def cosine(candidate: list[float]) -> float:
            return sum(a * b for a, b in zip(embedding, candidate)) / (
                math.sqrt(sum(a * a for a in embedding)) * math.sqrt(sum(b * b for b in candidate)) or 1.0
            )
        scored = [_candidate(item, cosine(item["embedding"])) for item in self._items.values()]
        return sorted(scored, key=lambda value: (-value["score"], value["id"]))[:top_k]


class VectorRetriever:
    def __init__(self, store: VectorStore | None = None, embedder: DeterministicEmbedder | None = None):
        self.store = store or VectorStore()
        self.embedder = embedder or DeterministicEmbedder()

    def index(self, items: Iterable[dict]) -> None:
        self.store.upsert(items)

    async def retrieve(self, query: str, top_k: int = 10, **_: object) -> list[dict]:
        return self.store.search(self.embedder.embed(query), top_k)


class HybridRetriever:
    def __init__(self, keyword: KeywordRetriever | None = None, vector: VectorRetriever | None = None):
        self.keyword = keyword or KeywordRetriever()
        self.vector = vector or VectorRetriever()

    def index(self, items: Iterable[dict]) -> None:
        items = list(items)
        self.keyword.index(items)
        self.vector.index(items)

    async def retrieve(self, query: str, top_k: int = 10, **kwargs: object) -> list[dict]:
        keyword_hits, vector_hits = await self.keyword.retrieve(query, top_k=top_k, **kwargs), await self.vector.retrieve(query, top_k=top_k, **kwargs)
        scores: defaultdict[str, float] = defaultdict(float)
        records: dict[str, dict] = {}
        for rank, hit in enumerate(keyword_hits + vector_hits, start=1):
            scores[hit["id"]] += 1.0 / (60 + rank)
            records[hit["id"]] = hit
        return [dict(records[key], score=round(scores[key], 6)) for key in sorted(scores, key=lambda key: (-scores[key], key))[:top_k]]
