# ==========================================
# LLM cost estimation
# ==========================================
from __future__ import annotations

from dataclasses import dataclass

from sales_agent.config import get_settings


@dataclass(slots=True)
class CostEstimate:
    input_tokens: int
    output_tokens: int
    cost_usd: float


_MOCK = {
    "runable-pro": (2.50, 10.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "deepseek-chat": (0.14, 0.28),
}


def count_tokens(text: str) -> int:
    if not text:
        return 0
    # fallback: ~4 chars per token (tiktoken optional)
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, len(text) // 4)


def compute_cost_usd(model: str, input_text: str, output_text: str) -> CostEstimate:
    s = get_settings()
    in_t = count_tokens(input_text)
    out_t = count_tokens(output_text)
    if getattr(s, "llm_cost_mode", "mock") == "real":
        in_p = getattr(s, "llm_price_input_per_m", 2.50)
        out_p = getattr(s, "llm_price_output_per_m", 10.0)
    else:
        in_p, out_p = _MOCK.get(model, (2.50, 10.00))
    cost = (in_t * in_p + out_t * out_p) / 1_000_000
    return CostEstimate(input_tokens=in_t, output_tokens=out_t, cost_usd=cost)
