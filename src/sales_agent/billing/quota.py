# ==========================================
# In-memory monthly quota tracker (DB-backed later)
# ==========================================
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sales_agent.billing.plans import LEADS, LLM_CALLS, MESSAGES, get_plan


class QuotaExceeded(Exception):
    def __init__(self, metric: str, limit: int) -> None:
        self.metric = metric
        self.limit = limit
        super().__init__(f"Quota exceeded for {metric}: limit={limit}")


class QuotaService:
    def __init__(self) -> None:
        # key: (tenant_id, yyyymm, metric) -> count
        self._usage: dict[tuple[str, str, str], int] = defaultdict(int)

    def _period(self) -> str:
        return datetime.now(tz=timezone.utc).strftime("%Y%m")

    def check(self, tenant_id: str, plan_name: str, metric: str, amount: int = 1) -> None:
        plan = get_plan(plan_name)
        limit = plan.limit_for(metric)
        key = (tenant_id, self._period(), metric)
        if self._usage[key] + amount > limit:
            raise QuotaExceeded(metric, limit)

    def consume(self, tenant_id: str, plan_name: str, metric: str, amount: int = 1) -> int:
        self.check(tenant_id, plan_name, metric, amount)
        key = (tenant_id, self._period(), metric)
        self._usage[key] += amount
        return self._usage[key]

    def snapshot(self, tenant_id: str, plan_name: str) -> dict[str, dict[str, int]]:
        plan = get_plan(plan_name)
        period = self._period()
        out = {}
        for metric in (MESSAGES, LLM_CALLS, LEADS):
            used = self._usage[(tenant_id, period, metric)]
            out[metric] = {"used": used, "limit": plan.limit_for(metric)}
        return out


quota_service = QuotaService()
