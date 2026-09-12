"""Anthropic adapter skeleton with the same gateway contract."""

import json
from typing import Any, AsyncIterator

from .base import BaseProvider, ChatRequest, ChatResponse, StructuredResponse, TokenUsage
from ..errors import AuthenticationError, GatewayError, RateLimitError


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise GatewayError("Install the optional anthropic dependency to use AnthropicProvider", "anthropic", "MISSING_SDK") from exc
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        system = "\n".join(m.content for m in request.messages if m.role == "system")
        messages = [{"role": m.role, "content": m.content} for m in request.messages if m.role != "system"]
        try:
            response = await self.client.messages.create(
                model=request.model,
                system=system or None,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 1024,
            )
            prompt = int(getattr(response.usage, "input_tokens", 0))
            completion = int(getattr(response.usage, "output_tokens", 0))
            return ChatResponse(
                content="".join(getattr(block, "text", "") for block in response.content),
                model=response.model,
                usage=TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion, estimated_cost_usd=0.0),
                finish_reason=response.stop_reason or "stop",
            )
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        response = await self.chat(request)
        yield response.content

    async def structured_chat(self, request: ChatRequest, schema: dict[str, Any]) -> StructuredResponse:
        response = await self.chat(request)
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise GatewayError("Provider returned invalid JSON", "anthropic", "INVALID_JSON") from exc
        return StructuredResponse(data=data, model=response.model, usage=response.usage, finish_reason=response.finish_reason)

    async def tool_call(self, request: ChatRequest, tools: list[dict[str, Any]]) -> dict[str, Any]:
        response = await self.chat(request)
        return {"content": response.content, "tools": tools}

    def normalize_error(self, error: Exception) -> GatewayError:
        text = str(error).lower()
        if "401" in text or "authentication" in text:
            return AuthenticationError("anthropic")
        if "429" in text or "overloaded" in text or "rate limit" in text:
            return RateLimitError(60, "anthropic")
        return GatewayError(str(error), "anthropic")

