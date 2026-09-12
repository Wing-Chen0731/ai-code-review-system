"""Stable provider contract used by the rest of the gateway."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from pydantic import BaseModel, ConfigDict, Field

from ..errors import GatewayError


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    content: str
    name: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1)
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    response_format: dict[str, Any] | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0.0)


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: TokenUsage
    finish_reason: str
    raw_response: dict[str, Any] | None = None


class StructuredResponse(BaseModel):
    data: dict[str, Any]
    model: str
    usage: TokenUsage
    finish_reason: str = "stop"


class BaseProvider(ABC):
    """All providers expose the same four async capabilities."""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def structured_chat(self, request: ChatRequest, schema: dict[str, Any]) -> StructuredResponse:
        raise NotImplementedError

    @abstractmethod
    async def tool_call(self, request: ChatRequest, tools: list[dict[str, Any]]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_error(self, error: Exception) -> GatewayError:
        raise NotImplementedError

