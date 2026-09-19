# ==========================================
# LLM client — mock + HTTP real mode
# ==========================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from sales_agent.ai.pricing import compute_cost_usd
from sales_agent.config import get_settings
from sales_agent.resilience.breaker import get_breaker


@dataclass(slots=True)
class LLMResponse:
    text: str
    model: str
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict | None = None


class LLMClient:
    def __init__(self) -> None:
        s = get_settings()
        self.api_key = getattr(s, "runable_api_key", "disabled")
        self.base_url = getattr(s, "runable_base_url", "https://api.runable.com/v1").rstrip("/")
        self.model = getattr(s, "ai_default_model", "runable-pro")
        self._breaker = get_breaker("llm")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        model_name = model or self.model

        # Mock mode when no real key
        if not self.api_key or self.api_key == "disabled":
            text = self._mock_reply(user_prompt)
            cost = compute_cost_usd(model_name, system_prompt + user_prompt, text)
            return LLMResponse(
                text=text,
                model=model_name,
                cost_usd=cost.cost_usd,
                input_tokens=cost.input_tokens,
                output_tokens=cost.output_tokens,
            )

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async def _do() -> dict:
            r = await self._client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()

        data = await self._breaker.call(_do)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        cost = compute_cost_usd(model_name, system_prompt + user_prompt, text)
        return LLMResponse(
            text=text,
            model=data.get("model", model_name),
            cost_usd=cost.cost_usd,
            input_tokens=cost.input_tokens,
            output_tokens=cost.output_tokens,
            raw=data,
        )

    def _mock_reply(self, user_prompt: str) -> str:
        # deterministic simple planner-style JSON-ish reply for tests
        if "JSON" in user_prompt or "json" in user_prompt:
            return '{"action":"send_message","channel":"bale","text":"سلام، پیام شما دریافت شد."}'
        return "سلام، پیام شما دریافت شد. به زودی پاسخ می‌دهیم."

    async def aclose(self) -> None:
        await self._client.aclose()
