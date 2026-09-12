"""Deterministic provider used by local development and CI."""

from typing import Any, AsyncIterator

from .base import BaseProvider, ChatRequest, ChatResponse, StructuredResponse, TokenUsage
from ..errors import GatewayError, RateLimitError


class MockProvider(BaseProvider):
    def __init__(self, responses: dict[str, str] | None = None, *, fail_times: int = 0):
        self.responses = responses or {}
        self.fail_times = fail_times
        self.calls = 0

    def _usage(self, request: ChatRequest) -> TokenUsage:
        prompt = sum(len(message.content.split()) for message in request.messages)
        completion = 8
        return TokenUsage(
            prompt_tokens=max(prompt, 1),
            completion_tokens=completion,
            total_tokens=max(prompt, 1) + completion,
            estimated_cost_usd=0.001,
        )

    def _maybe_fail(self, request: ChatRequest) -> None:
        self.calls += 1
        content = request.messages[-1].content
        if "trigger_rate_limit" in content or self.calls <= self.fail_times:
            raise RateLimitError(retry_after=0, provider="mock")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self._maybe_fail(request)
        content = request.messages[-1].content
        return ChatResponse(
            content=self.responses.get(content, "Mock response: no issues found."),
            model="mock-model",
            usage=self._usage(request),
            finish_reason="stop",
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        response = await self.chat(request)
        for chunk in response.content.split():
            yield f"{chunk} "

    async def structured_chat(self, request: ChatRequest, schema: dict[str, Any]) -> StructuredResponse:
        self._maybe_fail(request)
        return StructuredResponse(
            data={"findings": []},
            model="mock-model",
            usage=self._usage(request),
        )

    async def tool_call(self, request: ChatRequest, tools: list[dict[str, Any]]) -> dict[str, Any]:
        self._maybe_fail(request)
        return {"tool": tools[0].get("name", "mock_tool") if tools else "mock_tool", "arguments": {}}

    def normalize_error(self, error: Exception) -> GatewayError:
        return error if isinstance(error, GatewayError) else GatewayError(str(error), provider="mock")

