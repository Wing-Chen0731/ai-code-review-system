"""OpenAI-compatible provider. The SDK is imported only when this adapter is used."""

import json
from typing import Any, AsyncIterator

from .base import BaseProvider, ChatRequest, ChatResponse, StructuredResponse, TokenUsage
from ..errors import AuthenticationError, GatewayError, RateLimitError


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, base_url: str | None = None, pricing: dict[str, dict[str, float]] | None = None):
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise GatewayError("Install the optional openai dependency to use OpenAIProvider", "openai", "MISSING_SDK") from exc
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.pricing = pricing or {
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.00060},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        }

    async def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=[message.model_dump() for message in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
                response_format=request.response_format,
            )
            usage = self._calculate_usage(response.usage, request.model)
            return ChatResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage=usage,
                finish_reason=response.choices[0].finish_reason or "stop",
                raw_response=response.model_dump(),
            )
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        try:
            stream = await self.client.chat.completions.create(
                model=request.model,
                messages=[message.model_dump() for message in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                text = chunk.choices[0].delta.content if chunk.choices else None
                if text:
                    yield text
        except Exception as exc:
            raise self.normalize_error(exc) from exc

    async def structured_chat(self, request: ChatRequest, schema: dict[str, Any]) -> StructuredResponse:
        response = await self.chat(request.model_copy(update={"response_format": {"type": "json_object"}}))
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise GatewayError("Provider returned invalid JSON", "openai", "INVALID_JSON") from exc
        return StructuredResponse(data=data, model=response.model, usage=response.usage, finish_reason=response.finish_reason)

    async def tool_call(self, request: ChatRequest, tools: list[dict[str, Any]]) -> dict[str, Any]:
        response = await self.chat(request.model_copy(update={"tools": tools}))
        return {"content": response.content, "raw_response": response.raw_response or {}}

    def normalize_error(self, error: Exception) -> GatewayError:
        text = str(error).lower()
        if "401" in text or "authentication" in text:
            return AuthenticationError("openai")
        if "429" in text or "rate limit" in text:
            return RateLimitError(60, "openai")
        return GatewayError(str(error), "openai")

    def _calculate_usage(self, usage: Any, model: str) -> TokenUsage:
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        pricing = self.pricing.get(model, {"prompt": 0.0, "completion": 0.0})
        cost = prompt * pricing["prompt"] / 1000 + completion * pricing["completion"] / 1000
        return TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=int(getattr(usage, "total_tokens", prompt + completion) or prompt + completion),
            estimated_cost_usd=round(cost, 8),
        )

