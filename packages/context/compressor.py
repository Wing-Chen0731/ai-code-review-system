"""Budget-aware context compression."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4)) if text else 0


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    return text[: max(0, max_tokens) * 4]


class ContextCompressor:
    def compress(self, chunks: Sequence[Mapping], max_tokens: int) -> list[dict]:
        remaining = max_tokens
        output: list[dict] = []
        priority = {"changed": 0, "function": 1, "caller": 2, "callee": 3, "retrieved": 4}
        ordered = sorted(enumerate(chunks), key=lambda pair: (priority.get(pair[1].get("reference_type", "retrieved"), 5), pair[0]))
        for _, chunk in ordered:
            text = str(chunk.get("content", ""))
            cost = estimate_tokens(text)
            if not text or remaining <= 0:
                continue
            item = dict(chunk)
            if cost > remaining:
                item["content"] = truncate_to_tokens(text, remaining)
                item["truncated"] = True
                cost = estimate_tokens(item["content"])
            if item["content"]:
                output.append(item)
                remaining -= cost
        return output
