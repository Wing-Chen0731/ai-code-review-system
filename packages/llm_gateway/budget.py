from collections import defaultdict

from .errors import BudgetExceededError


class InMemoryBudgetController:
    def __init__(self, default_limit: float = 100.0):
        self.default_limit = default_limit
        self.used: dict[str, float] = defaultdict(float)
        self.limits: dict[str, float] = {}

    def set_limit(self, tenant_id: str, limit: float) -> None:
        self.limits[tenant_id] = limit

    async def check_budget(self, tenant_id: str, estimated_cost: float) -> bool:
        used = self.used[tenant_id]
        limit = self.limits.get(tenant_id, self.default_limit)
        if used + estimated_cost > limit:
            raise BudgetExceededError(tenant_id, used, limit)
        return True

    async def record_cost(self, tenant_id: str, cost: float) -> None:
        self.used[tenant_id] += cost

