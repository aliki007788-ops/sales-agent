from sales_agent.billing.plans import get_plan, estimate_monthly_llm_cost_usd


def test_pro_limits():
    p = get_plan("pro")
    assert p.max_messages_per_month == 1000
    assert p.monthly_price_irr == 15_000_000


def test_cost_estimate():
    assert estimate_monthly_llm_cost_usd("pro") > 0
    assert estimate_monthly_llm_cost_usd("enterprise") == 0
