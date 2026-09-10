"""阶段 1 的领域模型：数据契约优先，避免 LLM 输出直接进入交付层。"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewTaskStatus(StrEnum):
    RECEIVED = "RECEIVED"
    CONTEXT_READY = "CONTEXT_READY"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    """支持 Finding 的可审计证据；证据必须能回到输入上下文。"""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="diff、rule、test、documentation 等来源")
    quote: str = Field(min_length=1, description="来自代码或规则上下文的最小必要摘录")
    rationale: str = Field(min_length=1, description="为什么这段证据支持该 finding")
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @field_validator("line_end")
    @classmethod
    def end_must_not_precede_start(cls, value: int | None, info: Any) -> int | None:
        start = info.data.get("line_start")
        if value is not None and start is not None and value < start:
            raise ValueError("evidence line_end must be >= line_start")
        return value


class Finding(BaseModel):
    """一个可定位、可解释、可被用户反馈的审查发现。"""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    message: str = Field(min_length=1)

    @field_validator("line_end")
    @classmethod
    def end_must_not_precede_start(cls, value: int, info: Any) -> int:
        start = info.data.get("line_start")
        if start is not None and value < start:
            raise ValueError("line_end must be >= line_start")
        return value

    def validate(self, file_line_count: int, *, changed_lines: set[int] | None = None) -> "Finding":
        """验证落点是否在文件范围内，并可选地限制在 Diff 的 changed lines。"""

        if file_line_count < 1:
            raise ValueError("file_line_count must be positive")
        if self.line_end > file_line_count:
            raise ValueError(
                f"finding {self.file_path}:{self.line_start}-{self.line_end} "
                f"exceeds file length {file_line_count}"
            )
        if changed_lines is not None:
            finding_lines = set(range(self.line_start, self.line_end + 1))
            if not finding_lines.issubset(changed_lines):
                raise ValueError("finding must land entirely on changed lines")
        return self


class TaskEvent(BaseModel):
    """状态机事件；事件日志是重放与指标计算的事实来源。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str] = Field(default_factory=dict)


class ReviewTask(BaseModel):
    """一次 PR 审查任务及其受控状态流转。"""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    pull_request_number: int = Field(ge=1)
    status: ReviewTaskStatus = ReviewTaskStatus.RECEIVED
    findings: list[Finding] = Field(default_factory=list)
    events: list[TaskEvent] = Field(default_factory=list)

    _TRANSITIONS: dict[ReviewTaskStatus, set[ReviewTaskStatus]] = {
        ReviewTaskStatus.RECEIVED: {ReviewTaskStatus.CONTEXT_READY, ReviewTaskStatus.CANCELLED},
        ReviewTaskStatus.CONTEXT_READY: {ReviewTaskStatus.RUNNING, ReviewTaskStatus.CANCELLED},
        ReviewTaskStatus.RUNNING: {ReviewTaskStatus.VALIDATING, ReviewTaskStatus.FAILED, ReviewTaskStatus.CANCELLED},
        ReviewTaskStatus.VALIDATING: {ReviewTaskStatus.PUBLISHED, ReviewTaskStatus.FAILED},
        ReviewTaskStatus.PUBLISHED: set(),
        ReviewTaskStatus.FAILED: set(),
        ReviewTaskStatus.CANCELLED: set(),
    }

    def transition(self, target: ReviewTaskStatus, *, reason: str | None = None) -> "ReviewTask":
        allowed = self._TRANSITIONS[self.status]
        if target not in allowed:
            raise ValueError(f"illegal transition: {self.status} -> {target}")
        self.status = target
        self.events.append(TaskEvent(name=f"status.{target}", metadata={"reason": reason} if reason else {}))
        return self

