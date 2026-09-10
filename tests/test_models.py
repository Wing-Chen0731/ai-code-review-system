from packages.models import Finding, ReviewTask, ReviewTaskStatus, Severity


def test_review_task_happy_path_and_terminal_state():
    task = ReviewTask(task_id="t-1", repository="demo/repo", pull_request_number=7)
    for state in (
        ReviewTaskStatus.CONTEXT_READY,
        ReviewTaskStatus.RUNNING,
        ReviewTaskStatus.VALIDATING,
        ReviewTaskStatus.PUBLISHED,
    ):
        task.transition(state)
    assert task.status is ReviewTaskStatus.PUBLISHED
    assert len(task.events) == 4


def test_finding_validate_accepts_in_range_changed_lines():
    finding = Finding(
        file_path="src/app.py",
        line_start=12,
        line_end=12,
        severity=Severity.HIGH,
        confidence=0.91,
        message="Unsafe interpolation",
    )
    assert finding.validate(20, changed_lines={12}) is finding


def test_finding_validate_rejects_out_of_range_line():
    finding = Finding(
        file_path="src/app.py",
        line_start=12,
        line_end=12,
        severity=Severity.HIGH,
        confidence=0.91,
        message="Unsafe interpolation",
    )
    try:
        finding.validate(10)
    except ValueError as exc:
        assert "exceeds file length" in str(exc)
    else:
        raise AssertionError("expected invalid line to be rejected")

