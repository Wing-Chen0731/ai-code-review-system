import pytest

from packages.llm_gateway.adapters.base import ChatMessage, ChatRequest
from packages.llm_gateway.adapters.mock_adapter import MockProvider
from packages.llm_gateway.errors import RateLimitError


@pytest.mark.asyncio
async def test_mock_provider_contract():
    provider = MockProvider()
    request = ChatRequest(messages=[ChatMessage(role="user", content="Hello")], model="test-model")
    response = await provider.chat(request)
    structured = await provider.structured_chat(request, schema={"type": "object"})
    chunks = [chunk async for chunk in provider.stream_chat(request)]
    tool_result = await provider.tool_call(request, [{"name": "lookup"}])
    assert response.content
    assert response.usage.total_tokens > 0
    assert structured.data == {"findings": []}
    assert "Mock" in "".join(chunks)
    assert tool_result["tool"] == "lookup"


@pytest.mark.asyncio
async def test_mock_provider_normalizes_rate_limit_trigger():
    provider = MockProvider()
    request = ChatRequest(messages=[ChatMessage(role="user", content="trigger_rate_limit")], model="test-model")
    with pytest.raises(RateLimitError):
        await provider.chat(request)

