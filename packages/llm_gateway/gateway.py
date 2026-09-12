from pathlib import Path
from typing import Any

from .adapters.anthropic_adapter import AnthropicProvider
from .adapters.base import BaseProvider, ChatMessage, ChatRequest, StructuredResponse
from .adapters.local_adapter import LocalModelProvider
from .adapters.mock_adapter import MockProvider
from .adapters.openai_adapter import OpenAIProvider
from .budget import InMemoryBudgetController
from .config import GatewaySettings
from .factory import ProviderFactory
from .observability import CallLogger, elapsed_ms, new_trace_id
from .prompt_manager import PromptManager
from .reliability import CircuitBreaker, call_with_retry, call_with_timeout
from .router import ModelRouter
from .security import redact_sensitive
from .usage_repository import InMemoryUsageRepository


def register_builtin_providers() -> None:
    ProviderFactory.register("mock", MockProvider)
    ProviderFactory.register("openai", OpenAIProvider)
    ProviderFactory.register("anthropic", AnthropicProvider)
    ProviderFactory.register("local", LocalModelProvider)


class LLMGateway:
    def __init__(
        self,
        settings: GatewaySettings | None = None,
        *,
        router: ModelRouter | None = None,
        prompt_manager: PromptManager | None = None,
        usage_repo: InMemoryUsageRepository | None = None,
        budget: InMemoryBudgetController | None = None,
        providers: dict[str, BaseProvider] | None = None,
    ):
        register_builtin_providers()
        self.settings = settings or GatewaySettings()
        self.router = router or ModelRouter(self.settings.models_config_path)
        self.prompt_manager = prompt_manager or PromptManager(self.settings.prompt_dir)
        self.usage_repo = usage_repo or InMemoryUsageRepository()
        self.budget = budget or InMemoryBudgetController(self.settings.budget_default_limit_usd)
        self.circuit_breaker = CircuitBreaker()
        self.call_logger = CallLogger()
        self.providers = providers or {}

    def _get_provider(self, provider_name: str) -> BaseProvider:
        if provider_name in self.providers:
            return self.providers[provider_name]
        credentials: dict[str, Any] = {}
        if provider_name == "openai":
            credentials = {"api_key": self.settings.openai_api_key}
        elif provider_name == "anthropic":
            credentials = {"api_key": self.settings.anthropic_api_key}
        elif provider_name == "local":
            credentials = {}
        provider = ProviderFactory.create(provider_name, **credentials)
        self.providers[provider_name] = provider
        return provider

    def _load_schema(self) -> dict[str, Any]:
        import yaml

        return yaml.safe_load(Path(self.settings.schema_path).read_text(encoding="utf-8"))

    async def review_code(self, diff: str, context: str, tenant_id: str, *, provider_override: str | None = None) -> dict[str, Any]:
        route = self.router.route("code_review")
        trace_id = new_trace_id()
        await self.budget.check_budget(tenant_id, float(route["budget_per_call"]))
        prompt = self.prompt_manager.render(
            "code_review",
            "v1",
            diff=redact_sensitive(diff),
            context=redact_sensitive(context),
        )
        primary = route["primary"]
        provider_name = provider_override or primary["provider"]
        provider = self._get_provider(provider_name)
        request = ChatRequest(
            messages=[ChatMessage(role="user", content=prompt)],
            model=primary["model"],
            temperature=primary.get("temperature", 0.2),
            max_tokens=primary.get("max_tokens"),
        )

        start = __import__("time").perf_counter()
        response: StructuredResponse = await self.circuit_breaker.call(
            lambda: call_with_retry(
                lambda: call_with_timeout(
                    provider.structured_chat(request, self._load_schema()),
                    timeout_seconds=route.get("timeout_seconds", 60),
                ),
                max_retries=route.get("max_retries", 2),
            )
        )
        duration = elapsed_ms(start)
        chat_response = response.model_copy(update={"data": response.data})
        await self.usage_repo.record(trace_id, tenant_id, response.usage, response.model)
        await self.budget.record_cost(tenant_id, response.usage.estimated_cost_usd)
        self.call_logger.log_call(request, response, duration, trace_id)  # type: ignore[arg-type]
        return {
            "trace_id": trace_id,
            "findings": response.data.get("findings", []),
            "model": response.model,
            "usage": response.usage.model_dump(),
            "duration_ms": round(duration, 3),
        }

