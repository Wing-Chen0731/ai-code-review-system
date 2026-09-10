#!/usr/bin/env python3
"""Defensive mapping from AI-reported old-file lines to PR comment lines.

The script intentionally does not trust an AI line number. It parses hunk headers,
tracks old/new cursors, rejects deleted lines, and only emits a commentable new
line when the target is present in the resulting file.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class LineMapping:
    old_line: int | None
    new_line: int | None
    kind: str  # context, added, deleted


def parse_mappings(diff: str) -> list[LineMapping]:
    mappings: list[LineMapping] = []
    old_cursor = new_cursor = 0
    in_hunk = False

    for raw_line in diff.splitlines():
        match = HUNK_RE.match(raw_line)
        if match:
            old_cursor = int(match.group(1))
            new_cursor = int(match.group(3))
            in_hunk = True
            continue
        if not in_hunk or raw_line.startswith(("diff ", "--- ", "+++ ")):
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            mappings.append(LineMapping(None, new_cursor, "added"))
            new_cursor += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            mappings.append(LineMapping(old_cursor, None, "deleted"))
            old_cursor += 1
        elif raw_line.startswith(" "):
            mappings.append(LineMapping(old_cursor, new_cursor, "context"))
            old_cursor += 1
            new_cursor += 1
        elif raw_line.startswith("\\"):
            # The '\\ No newline...' marker has no line number of its own.
            continue
        else:
            raise ValueError(f"unexpected diff line inside hunk: {raw_line!r}")
    return mappings


def map_old_range_to_new(diff: str, old_start: int, old_end: int) -> tuple[int, int] | None:
    if old_start < 1 or old_end < old_start:
        raise ValueError("invalid old line range")
    mappings = parse_mappings(diff)
    selected = [m for m in mappings if m.old_line is not None and old_start <= m.old_line <= old_end]
    if not selected:
        return None
    if any(m.new_line is None for m in selected):
        # A deleted line has no legal GitHub review anchor. Do not guess silently.
        return None
    new_lines = [m.new_line for m in selected if m.new_line is not None]
    return min(new_lines), max(new_lines)


def main() -> int:
    fixture_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/malicious_diff.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    finding = fixture["ai_finding"]
    mapped = map_old_range_to_new(
        fixture["diff"], finding["line_start"], finding["line_end"]
    )
    expected = fixture["expected"]
    if mapped != (expected["mapped_line_start"], expected["mapped_line_end"]):
        raise AssertionError(f"mapping mismatch: got {mapped}, expected {expected}")
    print(
        f"{finding['file_path']} old:{finding['line_start']}-{finding['line_end']} "
        f"=> new:{mapped[0]}-{mapped[1]} commentable={expected['commentable']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

