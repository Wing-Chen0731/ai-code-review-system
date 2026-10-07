"""Compare retrieval strategies on a tiny golden dataset."""

from __future__ import annotations

from dataclasses import dataclass

from packages.context.chunker import CodeChunker
from packages.context.embedder import CodeEmbedder
from packages.context.retriever import HybridRetriever, KeywordRetriever, VectorRetriever
from packages.context.reranker import Reranker


@dataclass
class RetrievalQuery:
    query: str
    relevant_ids: set[str]


class RetrievalExperiment:
    def __init__(self, chunks: list, queries: list[RetrievalQuery]):
        self.chunks = chunks
        self.queries = queries

    async def run(self, top_k: int = 10) -> list[dict]:
        items = await CodeEmbedder().embed_chunks(self.chunks)
        strategies = {
            "keyword": KeywordRetriever(),
            "vector": VectorRetriever(),
            "hybrid": HybridRetriever(),
        }
        for strategy in strategies.values():
            strategy.index(items)
        reranker = Reranker()
        results: list[dict] = []
        for name, strategy in strategies.items():
            for query in self.queries:
                hits = await strategy.retrieve(query.query, top_k=top_k)
                if name == "hybrid":
                    hits = await reranker.rerank(query.query, hits, top_k=top_k)
                returned = {hit["id"] for hit in hits}
                tp = len(returned & query.relevant_ids)
                precision = tp / max(1, len(returned))
                recall = tp / max(1, len(query.relevant_ids))
                results.append({"strategy": name, "query": query.query,
                                "precision_at_k": round(precision, 4),
                                "recall_at_k": round(recall, 4),
                                "f1": round(2 * precision * recall / max(1e-9, precision + recall), 4)})
        return results


async def demo() -> list[dict]:
    chunks = CodeChunker().chunk("sample.py", "def authenticate(token):\n    return token is not None\n\ndef unrelated():\n    return 1\n")
    return await RetrievalExperiment(chunks, [RetrievalQuery("authenticate token", {chunks[0].chunk_id})]).run()


if __name__ == "__main__":
    import asyncio
    for row in asyncio.run(demo()):
        print(row)
