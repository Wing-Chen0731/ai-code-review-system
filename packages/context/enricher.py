"""Enrich changed code with local symbols, callers, callees and imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ast_analyzer import ASTAnalyzer, Symbol


@dataclass
class EnrichedSymbol:
    symbol: Symbol
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


class ContextEnricher:
    """Produce deterministic local context without requiring a language server."""

    def enrich(self, file_path: str, source: str, changed_lines: set[int]) -> list[EnrichedSymbol]:
        analyzer = ASTAnalyzer(source, file_path)
        table = analyzer.symbol_table()
        result: list[EnrichedSymbol] = []
        for symbol in table.symbols.values():
            if symbol.end_line < min(changed_lines or {1}) or symbol.start_line > max(changed_lines or {0}):
                continue
            result.append(
                EnrichedSymbol(
                    symbol=symbol,
                    callers=sorted(table.reverse_call_graph.get(symbol.qualified_name, [])),
                    callees=sorted(table.call_graph.get(symbol.qualified_name, [])),
                    imports=list(table.imports),
                )
            )
        return result


class CrossFileAnalyzer:
    """Optional adapter for repository-wide symbol search."""

    def __init__(self, repository_client: Any | None = None):
        self.repository_client = repository_client

    async def find_references(self, owner: str, repo: str, symbol_name: str) -> list[dict[str, Any]]:
        if self.repository_client is None:
            return []
        return await self.repository_client.search_code(owner, repo, symbol_name)
