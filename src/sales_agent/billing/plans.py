# ==========================================
# Pricing plans — revised for LLM cost reality
# ==========================================
from __future__ import annotations

from dataclasses import dataclass

MESSAGES = "messages_sent"
LLM_CALLS = "llm_calls"
LEADS = "leads_created"


@dataclass(frozen=True, slots=True)
class Plan:
    name: str
    display_name: str
    monthly_price_irr: int
    max_messages_per_month: int
    max_llm_calls_per_month: int
    max_leads_per_month: int
    max_channels: int
    max_seats: int

    def limit_for(self, metric: str) -> int:
        return {
            MESSAGES: self.max_messages_per_month,
            LLM_CALLS: self.max_llm_calls_per_month,
            LEADS: self.max_leads_per_month,
        }.get(metric, 0)


PLANS: dict[str, Plan] = {
    "free": Plan("free", "رایگان", 0, 100, 200, 50, 1, 1),
    "pro": Plan("pro", "حرفه‌ای", 15_000_000, 1_000, 2_000, 500, 4, 3),
    "business": Plan("business", "کسب‌وکار", 45_000_000, 5_000, 10_000, 2_500, 7, 10),
    "enterprise": Plan("enterprise", "سازمانی", 0, 10**9, 10**9, 10**9, 10, 1000),
}


def get_plan(name: str) -> Plan:
    return PLANS.get(name, PLANS["free"])


def estimate_monthly_llm_cost_usd(plan_name: str, cost_per_call: float = 0.008) -> float:
    p = get_plan(plan_name)
    if p.max_llm_calls_per_month >= 10**9:
        return 0.0
    return p.max_llm_calls_per_month * cost_per_call
