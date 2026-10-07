from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class CodeReference(BaseModel):
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str
    symbol_name: str | None = None
    reference_type: str


class DiffContext(BaseModel):
    file_path: str
    change_type: str
    hunks: list[dict[str, Any]]
    changed_lines: list[int]


class ReviewContext(BaseModel):
    task_id: str
    repository: str
    pr_number: int = Field(ge=1)
    base_sha: str
    head_sha: str
    diff_contexts: list[DiffContext]
    code_references: list[CodeReference]
    pr_title: str
    pr_description: str | None = None
    project_intent: str | None = None
    estimated_tokens: int = Field(ge=0)
    built_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    builder_version: str = "v1"

