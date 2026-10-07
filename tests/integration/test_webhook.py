import hashlib
import hmac
import json

import pytest

from integrations.github.webhook import GitHubWebhookHandler, GitHubWebhookVerifier, WebhookDeduplicator


@pytest.mark.asyncio
async def test_webhook_verifies_and_deduplicates_pull_request_event():
    secret = "secret"
    payload = {"action": "opened", "repository": {"full_name": "acme/demo", "name": "demo", "owner": {"login": "acme"}}, "pull_request": {"number": 7, "base": {"sha": "base"}, "head": {"sha": "head"}}}
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    queued = []
    async def enqueue(task):
        queued.append(task)
    handler = GitHubWebhookHandler(GitHubWebhookVerifier(secret), WebhookDeduplicator(), enqueue)
    first = await handler.handle(body, signature, "pull_request", "delivery-1", payload)
    second = await handler.handle(body, signature, "pull_request", "delivery-1", payload)
    assert first["enqueued"] is True
    assert second["status"] == "duplicate"
    assert len(queued) == 1


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature():
    handler = GitHubWebhookHandler(GitHubWebhookVerifier("secret"), WebhookDeduplicator(), lambda task: None)
    with pytest.raises(PermissionError):
        await handler.handle(b"{}", "sha256=bad", "ping", "delivery-2", {})
