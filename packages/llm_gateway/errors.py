"""Provider-independent error taxonomy."""


class GatewayError(Exception):
    def __init__(self, message: str, provider: str = "gateway", code: str = "UNKNOWN"):
        self.message = message
        self.provider = provider
        self.code = code
        super().__init__(message)


class RateLimitError(GatewayError):
    def __init__(self, retry_after: int = 1, provider: str = "gateway"):
        super().__init__(f"Rate limited, retry after {retry_after}s", provider, "RATE_LIMIT")
        self.retry_after = retry_after


class AuthenticationError(GatewayError):
    def __init__(self, provider: str):
        super().__init__("Authentication failed, check API key", provider, "AUTH_ERROR")


class ContextLengthExceededError(GatewayError):
    def __init__(self, provider: str, limit: int):
        super().__init__(f"Context length exceeded (limit: {limit} tokens)", provider, "CONTEXT_EXCEEDED")
        self.limit = limit


class GatewayTimeoutError(GatewayError):
    def __init__(self, provider: str, timeout_seconds: float):
        super().__init__(f"Request timed out after {timeout_seconds}s", provider, "TIMEOUT")
        self.timeout_seconds = timeout_seconds


class BudgetExceededError(GatewayError):
    def __init__(self, tenant_id: str, used: float, limit: float):
        super().__init__(f"Budget exceeded for {tenant_id}: {used:.6f} >= {limit:.6f}", "gateway", "BUDGET_EXCEEDED")
        self.tenant_id = tenant_id
        self.used = used
        self.limit = limit


class CircuitOpenError(GatewayError):
    def __init__(self):
        super().__init__("Circuit breaker is OPEN", "gateway", "CIRCUIT_OPEN")

