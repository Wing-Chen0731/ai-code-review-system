"""Timeout, retry, token bucket and circuit breaker primitives."""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .errors import CircuitOpenError, GatewayError, GatewayTimeoutError, RateLimitError

T = TypeVar("T")


async def call_with_timeout(operation: Awaitable[T], timeout_seconds: float = 30) -> T:
    try:
        return await asyncio.wait_for(operation, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise GatewayTimeoutError("gateway", timeout_seconds) from exc


async def call_with_retry(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 30.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except (RateLimitError, GatewayTimeoutError, GatewayError):
            if attempt >= max_retries:
                raise
            jitter = random.uniform(0, base_delay)
            delay = min(base_delay * (2**attempt) + jitter, max_delay)
            await sleep(delay)
    raise AssertionError("unreachable")


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        if capacity < 1 or refill_rate <= 0:
            raise ValueError("capacity must be >= 1 and refill_rate must be positive")
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        if tokens < 1 or tokens > self.capacity:
            return False
        async with self._lock:
            self._refill()
            if self.tokens < tokens:
                return False
            self.tokens -= tokens
            return True

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class CircuitBreaker:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = self.CLOSED
        self.last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self.state == self.OPEN:
                if self.last_failure_time is None or time.monotonic() - self.last_failure_time <= self.recovery_timeout:
                    raise CircuitOpenError()
                self.state = self.HALF_OPEN
        try:
            result = await operation()
        except Exception:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.monotonic()
                if self.failure_count >= self.failure_threshold:
                    self.state = self.OPEN
            raise
        async with self._lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = self.CLOSED
        return result


class FallbackStrategy:
    def __init__(self, primary: object, fallbacks: list[object]):
        self.primary = primary
        self.fallbacks = fallbacks

    async def call(self, operation: Callable[[object], Awaitable[T]]) -> T:
        last_error: Exception | None = None
        for provider in [self.primary, *self.fallbacks]:
            try:
                return await operation(provider)
            except (GatewayError, OSError) as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise GatewayError("No provider configured")

