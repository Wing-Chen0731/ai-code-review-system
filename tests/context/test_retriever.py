import pytest

from packages.context.chunker import CodeChunk
from packages.context.embedder import CodeEmbedder
from packages.context.retriever import HybridRetriever


@pytest.mark.asyncio
async def test_hybrid_retriever_returns_matching_chunk():
    chunks = [CodeChunk("a", "a.py", "def authenticate(token): pass", 1, 1)]
    items = await CodeEmbedder().embed_chunks(chunks)
    retriever = HybridRetriever()
    retriever.index(items)
    result = await retriever.retrieve("authenticate token")
    assert result[0]["id"] == "a"
