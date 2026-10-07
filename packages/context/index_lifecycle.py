"""Lifecycle hooks for invalidating and rebuilding repository indexes."""

from __future__ import annotations

from collections.abc import Iterable

from .chunker import CodeChunker
from .embedder import CodeEmbedder
from .retriever import VectorStore


class IndexLifecycleManager:
    def __init__(self, store: VectorStore | None = None, chunker: CodeChunker | None = None, embedder: CodeEmbedder | None = None):
        self.store = store or VectorStore()
        self.chunker = chunker or CodeChunker()
        self.embedder = embedder or CodeEmbedder()
        self.deleted_repositories: set[str] = set()

    async def reindex_files(self, files: Iterable[tuple[str, str]]) -> int:
        total = 0
        for file_path, content in files:
            self.store.delete_by_file(file_path)
            items = await self.embedder.embed_chunks(self.chunker.chunk(file_path, content))
            self.store.upsert(items)
            total += len(items)
        return total

    async def on_pr_merged(self, changed_files: Iterable[tuple[str, str]]) -> int:
        return await self.reindex_files(changed_files)

    def on_repository_deleted(self, repository: str) -> None:
        self.deleted_repositories.add(repository)
