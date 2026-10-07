"""Offline deterministic embeddings for local development and tests."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from .chunker import CodeChunk


class DeterministicEmbedder:
    def __init__(self, dimension: int = 64):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[\u4e00-\u9fff]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class CodeEmbedder:
    def __init__(self, embedder: DeterministicEmbedder | None = None):
        self.embedder = embedder or DeterministicEmbedder()

    async def embed_chunks(self, chunks: Iterable[CodeChunk]) -> list[dict]:
        return [{"chunk": chunk, "embedding": self.embedder.embed(chunk.content)} for chunk in chunks]
