from typing import Any

from pydantic import BaseModel, Field


class PullRequestTask(BaseModel):
    task_id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    pr_number: int = Field(ge=1)
    repository: str = Field(min_length=1)
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    trigger: str = "opened"


def task_from_pull_request_event(payload: dict[str, Any], action: str, task_id: str) -> PullRequestTask:
    pr = payload["pull_request"]
    repository = payload["repository"]
    owner = repository["owner"]["login"]
    return PullRequestTask(
        task_id=task_id,
        owner=owner,
        repo=repository["name"],
        repository=repository["full_name"],
        pr_number=pr["number"],
        base_sha=pr["base"]["sha"],
        head_sha=pr["head"]["sha"],
        trigger=action,
    )

