"""Build a bounded, traceable review context from a pull request."""

from __future__ import annotations

from typing import Any

from integrations.github.models import PullRequestTask

from .ast_analyzer import ASTAnalyzer
from .compressor import ContextCompressor, estimate_tokens
from .diff_parser import DiffParser
from .governance import should_skip_file
from .schema import CodeReference, DiffContext, ReviewContext


class ContextBuilder:
    def __init__(self, github_client: Any, retriever: Any | None = None, compressor: ContextCompressor | None = None):
        self.github_client = github_client
        self.retriever = retriever
        self.compressor = compressor or ContextCompressor()

    async def build(self, task: PullRequestTask) -> ReviewContext:
        pr = await self.github_client.get_pull_request(task.owner, task.repo, task.pr_number)
        files = await self.github_client.get_pr_files(task.owner, task.repo, task.pr_number)
        diffs: list[DiffContext] = []
        references: list[dict] = []
        for file_info in files:
            path = file_info.get("filename", "")
            patch = file_info.get("patch", "") or ""
            if should_skip_file(path)[0] or not patch:
                continue
            parsed = DiffParser().parse(path, patch)
            changed = sorted(parsed.changed_lines)
            diffs.append(DiffContext(file_path=path, change_type=parsed.change_type, hunks=[
                {"header": h.header, "old_start": h.old_start, "old_count": h.old_count,
                 "new_start": h.new_start, "new_count": h.new_count,
                 "lines": [line.__dict__ for line in h.lines]}
                for h in parsed.hunks
            ], changed_lines=changed))
            try:
                source = await self.github_client.get_file_content(task.owner, task.repo, path, task.head_sha)
            except Exception:
                source = ""
            if source:
                references.extend(self._local_references(path, source, set(changed)))
            for hunk in parsed.hunks:
                content = "\n".join(line.content for line in hunk.lines if line.new_line is not None)
                if content:
                    references.append({"reference_type": "changed", "file_path": path,
                                       "start_line": hunk.new_start, "end_line": hunk.new_start + hunk.new_count - 1,
                                       "content": content})

        if self.retriever is not None:
            query = f"{pr.get('title', '')}\n{pr.get('body', '') or ''}"
            references.extend(dict(item, reference_type="retrieved") for item in await self.retriever.retrieve(query, top_k=10))
        budgeted = self.compressor.compress(references, max_tokens=8000)
        code_refs = [CodeReference(**self._reference_payload(item)) for item in budgeted]
        return ReviewContext(
            task_id=task.task_id,
            repository=task.repository,
            pr_number=task.pr_number,
            base_sha=task.base_sha,
            head_sha=task.head_sha,
            pr_title=pr.get("title", ""),
            pr_description=pr.get("body"),
            diff_contexts=diffs,
            code_references=code_refs,
            estimated_tokens=estimate_tokens("\n".join(ref.content for ref in code_refs)),
        )

    @staticmethod
    def _local_references(path: str, source: str, changed: set[int]) -> list[dict]:
        table = ASTAnalyzer(source, path).symbol_table()
        output: list[dict] = []
        for symbol in table.symbols.values():
            if symbol.end_line < min(changed or {1}) or symbol.start_line > max(changed or {0}):
                continue
            lines = source.splitlines()
            output.append({"reference_type": "function" if symbol.kind == "function" else "class",
                           "file_path": path, "start_line": symbol.start_line, "end_line": symbol.end_line,
                           "symbol_name": symbol.qualified_name,
                           "content": "\n".join(lines[symbol.start_line - 1:symbol.end_line])})
        return output

    @staticmethod
    def _reference_payload(item: dict) -> dict:
        allowed = {"reference_type", "file_path", "start_line", "end_line", "symbol_name", "content"}
        payload = {key: value for key, value in item.items() if key in allowed}
        payload.setdefault("reference_type", "retrieved")
        payload.setdefault("file_path", "")
        payload.setdefault("start_line", 1)
        payload.setdefault("end_line", payload["start_line"])
        payload.setdefault("content", "")
        return payload
