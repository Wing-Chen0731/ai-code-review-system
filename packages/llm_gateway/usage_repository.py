from dataclasses import dataclass

from .adapters.base import TokenUsage


@dataclass(frozen=True)
class UsageRecord:
    trace_id: str
    tenant_id: str
    model: str
    usage: TokenUsage


class InMemoryUsageRepository:
    def __init__(self):
        self.records: list[UsageRecord] = []

    async def record(self, trace_id: str, tenant_id: str, usage: TokenUsage, model: str) -> None:
        self.records.append(UsageRecord(trace_id, tenant_id, model, usage))

    async def get_monthly_cost(self, tenant_id: str) -> float:
        return sum(record.usage.estimated_cost_usd for record in self.records if record.tenant_id == tenant_id)

