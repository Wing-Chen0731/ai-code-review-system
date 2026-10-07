"""GitHub webhook verification and idempotent event handling primitives."""

import hashlib
import hmac
from collections.abc import Awaitable, Callable
from typing import Any

from .models import PullRequestTask, task_from_pull_request_event


class GitHubWebhookVerifier:
    def __init__(self, secret: str):
        if not secret:
            raise ValueError("webhook secret must not be empty")
        self.secret = secret.encode("utf-8")

    def verify(self, payload_body: bytes, signature_header: str | None) -> bool:
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        received = signature_header.removeprefix("sha256=")
        if len(received) != hashlib.sha256().digest_size * 2:
            return False
        expected = hmac.new(self.secret, payload_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received)


class WebhookDeduplicator:
    """In-memory SET-NX equivalent for local tests; Redis can implement the same contract."""

    def __init__(self):
        self._delivery_ids: set[str] = set()

    async def is_duplicate(self, delivery_id: str) -> bool:
        if not delivery_id:
            raise ValueError("delivery_id must not be empty")
        if delivery_id in self._delivery_ids:
            return True
        self._delivery_ids.add(delivery_id)
        return False


class GitHubWebhookHandler:
    def __init__(
        self,
        verifier: GitHubWebhookVerifier,
        deduplicator: WebhookDeduplicator,
        enqueue: Callable[[PullRequestTask], Awaitable[None]],
    ):
        self.verifier = verifier
        self.deduplicator = deduplicator
        self.enqueue = enqueue

    async def handle(
        self,
        body: bytes,
        signature: str | None,
        event_type: str,
        delivery_id: str,
        payload: dict[str, Any],
    ) -> dict[str, str | bool]:
        if not self.verifier.verify(body, signature):
            raise PermissionError("invalid GitHub webhook signature")
        if await self.deduplicator.is_duplicate(delivery_id):
            return {"status": "duplicate", "enqueued": False}
        if event_type == "ping":
            return {"status": "ok", "enqueued": False}
        if event_type != "pull_request":
            return {"status": "ignored", "enqueued": False}
        action = payload.get("action")
        if action not in {"opened", "synchronize", "reopened"}:
            return {"status": "ignored", "enqueued": False}
        task = task_from_pull_request_event(payload, action, delivery_id)
        await self.enqueue(task)
        return {"status": "ok", "enqueued": True}

