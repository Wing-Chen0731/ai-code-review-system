import pytest

from integrations.github.models import PullRequestTask
from packages.context.builder import ContextBuilder


class MockGitHub:
    async def get_pull_request(self, owner, repo, number):
        return {"title": "Fix auth", "body": "Please review token validation"}

    async def get_pr_files(self, owner, repo, number):
        return [{"filename": "auth.py", "patch": "@@ -1,2 +1,4 @@\n def validate(token):\n+    if not token:\n+        return False\n     return True"}]

    async def get_file_content(self, owner, repo, path, ref):
        return "def validate(token):\n    if not token:\n        return False\n    return True\n"


@pytest.mark.asyncio
async def test_context_builder_creates_traceable_review_context():
    task = PullRequestTask(task_id="t1", owner="acme", repo="demo", repository="acme/demo", pr_number=3, base_sha="base", head_sha="head")
    context = await ContextBuilder(MockGitHub()).build(task)
    assert context.task_id == "t1"
    assert context.pr_title == "Fix auth"
    assert context.diff_contexts[0].changed_lines == [2, 3]
    assert context.code_references
    assert context.estimated_tokens > 0
