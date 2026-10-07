"""Semantic and fallback code chunking."""

from __future__ import annotations

from dataclasses import dataclass

from .ast_analyzer import ASTAnalyzer


@dataclass(frozen=True)
class CodeChunk:
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str = "code"
    symbol_name: str | None = None


class CodeChunker:
    def __init__(self, max_lines: int = 80, overlap_lines: int = 10):
        self.max_lines = max_lines
        self.overlap_lines = min(overlap_lines, max_lines - 1)

    def chunk(self, file_path: str, source: str) -> list[CodeChunk]:
        lines = source.splitlines()
        if not lines:
            return []
        analyzer = ASTAnalyzer(source, file_path)
        symbols = [s for s in analyzer.symbol_table().symbols.values() if s.kind in {"function", "class"}]
        chunks: list[CodeChunk] = []
        covered: set[int] = set()
        for symbol in sorted(symbols, key=lambda item: (item.start_line, item.end_line)):
            start = max(1, symbol.start_line)
            end = min(len(lines), symbol.end_line)
            if end - start + 1 > self.max_lines:
                end = start + self.max_lines - 1
            if start > end:
                continue
            covered.update(range(start, end + 1))
            chunks.append(self._make_chunk(file_path, lines, start, end, "symbol", symbol.qualified_name))

        for start in range(1, len(lines) + 1, max(1, self.max_lines - self.overlap_lines)):
            end = min(len(lines), start + self.max_lines - 1)
            if not covered.intersection(range(start, end + 1)) or not chunks:
                chunks.append(self._make_chunk(file_path, lines, start, end, "window", None))
            if end == len(lines):
                break
        return sorted(chunks, key=lambda item: (item.start_line, item.end_line, item.chunk_type))

    @staticmethod
    def _make_chunk(file_path: str, lines: list[str], start: int, end: int, kind: str, symbol: str | None) -> CodeChunk:
        return CodeChunk(
            chunk_id=f"{file_path}:{start}-{end}",
            file_path=file_path,
            content="\n".join(lines[start - 1:end]),
            start_line=start,
            end_line=end,
            chunk_type=kind,
            symbol_name=symbol,
        )
