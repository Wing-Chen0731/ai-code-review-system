"""Unified diff parsing with old/new line mappings for safe PR comments."""

import re
from dataclasses import dataclass, field


@dataclass
class DiffLine:
    content: str
    kind: str  # context, added, deleted
    old_line: int | None
    new_line: int | None


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[DiffLine] = field(default_factory=list)

    @property
    def changed_new_lines(self) -> list[int]:
        return [line.new_line for line in self.lines if line.kind == "added" and line.new_line is not None]


@dataclass
class ParsedDiff:
    file_path: str
    change_type: str
    hunks: list[DiffHunk]
    new_line_map: dict[int, int]
    diff_line_map: list[DiffLine] = field(default_factory=list)

    @property
    def changed_lines(self) -> list[int]:
        return [line.new_line for line in self.diff_line_map if line.kind == "added" and line.new_line is not None]

    @property
    def touched_lines(self) -> list[int]:
        return [line.new_line for line in self.diff_line_map if line.new_line is not None]

    def map_hunk_line(self, hunk_index: int, line_index: int) -> int | None:
        try:
            return self.hunks[hunk_index].lines[line_index].new_line
        except IndexError:
            return None


class DiffParser:
    HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    def parse(self, file_path: str, diff_text: str) -> ParsedDiff:
        hunks: list[DiffHunk] = []
        all_lines: list[DiffLine] = []
        new_line_map: dict[int, int] = {}
        current: DiffHunk | None = None
        old_cursor = new_cursor = 0
        content_index = 0

        for raw in diff_text.splitlines():
            match = self.HUNK_HEADER.match(raw)
            if match:
                current = DiffHunk(
                    old_start=int(match.group(1)),
                    old_count=int(match.group(2) or 1),
                    new_start=int(match.group(3)),
                    new_count=int(match.group(4) or 1),
                    header=raw,
                )
                hunks.append(current)
                old_cursor, new_cursor = current.old_start, current.new_start
                continue
            if current is None or raw.startswith(("diff ", "index ", "--- ", "+++ ", "new file mode", "deleted file mode", "similarity index", "rename ")):
                continue
            if raw.startswith("\\"):
                continue
            if raw.startswith("+"):
                line = DiffLine(raw[1:], "added", None, new_cursor)
                new_cursor += 1
            elif raw.startswith("-"):
                line = DiffLine(raw[1:], "deleted", old_cursor, None)
                old_cursor += 1
            elif raw.startswith(" "):
                line = DiffLine(raw[1:], "context", old_cursor, new_cursor)
                old_cursor += 1
                new_cursor += 1
            else:
                raise ValueError(f"unexpected diff line inside hunk: {raw!r}")
            current.lines.append(line)
            all_lines.append(line)
            if line.new_line is not None:
                new_line_map[content_index] = line.new_line
            content_index += 1

        return ParsedDiff(
            file_path=file_path,
            change_type=self._detect_change_type(diff_text),
            hunks=hunks,
            new_line_map=new_line_map,
            diff_line_map=all_lines,
        )

    @staticmethod
    def _detect_change_type(diff_text: str) -> str:
        if "new file mode" in diff_text:
            return "added"
        if "deleted file mode" in diff_text:
            return "deleted"
        if "rename from" in diff_text:
            return "renamed"
        return "modified"

