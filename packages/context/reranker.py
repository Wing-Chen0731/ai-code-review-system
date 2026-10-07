"""Deterministic reranking stage; replace with a cross-encoder in production."""

from __future__ import annotations

import re


class Reranker:
    async def rerank(self, query: str, candidates: list[dict], top_k: int = 10) -> list[dict]:
        query_terms = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]+", query.lower()))
        result = []
        for candidate in candidates:
            content = candidate.get("content", "").lower()
            exact = sum(content.count(term) for term in query_terms)
            value = dict(candidate)
            value["rerank_score"] = round(exact + candidate.get("score", 0.0), 6)
            result.append(value)
        return sorted(result, key=lambda item: (-item["rerank_score"], item.get("id", "")))[:top_k]
