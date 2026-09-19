# ==========================================
# src/sales_agent/config.py
# Version: 1.0 — Phase 1 Core Foundation
# ==========================================
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Autonomous Sales Agent"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    secret_key: str = Field(min_length=16, default="change-me-in-production-32chars!")
    api_key_prefix: str = "asa_"
    api_key_length: int = Field(default=32, ge=16, le=64)

    database_url: str = "postgresql+asyncpg://asa:asa@localhost:5432/asa"
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_echo: bool = False

    cors_origins: list[str] = Field(default_factory=list)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = False

    # LLM
    runable_api_key: str = "disabled"
    runable_base_url: str = "https://api.runable.com/v1"
    ai_default_model: str = "runable-pro"
    llm_cost_mode: str = "mock"  # mock | real
    llm_price_input_per_m: float = 2.50
    llm_price_output_per_m: float = 10.00

    # Rate limit
    rate_limit_max: int = 120
    rate_limit_window_seconds: float = 60.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
