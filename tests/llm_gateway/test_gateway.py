import pytest

from packages.llm_gateway.adapters.mock_adapter import MockProvider
from packages.llm_gateway.budget import InMemoryBudgetController
from packages.llm_gateway.config import GatewaySettings
from packages.llm_gateway.errors import BudgetExceededError, CircuitOpenError, RateLimitError
from packages.llm_gateway.gateway import LLMGateway
from packages.llm_gateway.reliability import CircuitBreaker, TokenBucket, call_with_retry
from packages.llm_gateway.security import redact_sensitive


@pytest.mark.asyncio
async def test_gateway_runs_without_real_model():
    provider = MockProvider()
    gateway = LLMGateway(GatewaySettings(), providers={"mock": provider})
    result = await gateway.review_code("password=secret@example.com", "context", "tenant-a")
    assert result["findings"] == []
    assert result["trace_id"]
    assert result["usage"]["total_tokens"] > 0
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_gateway_retries_rate_limit_and_records_usage():
    provider = MockProvider(fail_times=2)
    gateway = LLMGateway(GatewaySettings(), providers={"mock": provider})
    result = await gateway.review_code("diff", "context", "tenant-a")
    assert result["findings"] == []
    assert provider.calls == 3
    assert len(gateway.usage_repo.records) == 1


@pytest.mark.asyncio
async def test_budget_controller_rejects_over_limit():
    budget = InMemoryBudgetController(default_limit=0.01)
    budget.set_limit("tenant-a", 0.0001)
    gateway = LLMGateway(GatewaySettings(), budget=budget, providers={"mock": MockProvider()})
    with pytest.raises(BudgetExceededError):
        await gateway.review_code("diff", "context", "tenant-a")


@pytest.mark.asyncio
async def test_retry_uses_jittered_backoff_without_waiting_in_test():
    attempts = 0
    delays: list[float] = []

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RateLimitError(retry_after=0, provider="test")
        return "ok"

    async def fake_sleep(delay: float):
        delays.append(delay)

    assert await call_with_retry(operation, max_retries=2, base_delay=0.01, sleep=fake_sleep) == "ok"
    assert attempts == 3
    assert len(delays) == 2


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    async def fail():
        raise RuntimeError("provider down")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(fail)
    with pytest.raises(CircuitOpenError):
        await breaker.call(fail)


@pytest.mark.asyncio
async def test_token_bucket_limits_requests():
    bucket = TokenBucket(capacity=1, refill_rate=0.01)
    assert await bucket.acquire()
    assert not await bucket.acquire()


def test_redaction_removes_secrets_and_pii():
    text = "api_key=abc123 email=person@example.com card=4111-1111-1111-1111"
    redacted = redact_sensitive(text)
    assert "abc123" not in redacted
    assert "person@example.com" not in redacted
    assert "4111-1111-1111-1111" not in redacted

