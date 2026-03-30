"""
Application configuration loaded from environment variables via Pydantic Settings.

All tunable values must be declared here — no magic numbers in service code.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Logging
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./returns.db"

    # Return policy
    return_window_days: int = 30

    # Decision thresholds
    refund_threshold_amount: float = 500.0
    high_value_manual_review: bool = True
    auto_approve_score: float = 0.70

    restricted_product_types: list[str] = Field(default_factory=list)

    @field_validator("restricted_product_types", mode="before")
    @classmethod
    def parse_restricted_types(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(x) for x in value]
        if isinstance(value, str):
            import json

            s = value.strip()
            if s.startswith("["):
                return [str(x) for x in json.loads(s)]
            return [p.strip() for p in s.split(",") if p.strip()]
        return []

    # AI provider
    ai_provider: Literal["mock", "openai", "openai_compatible"] = "mock"
    ai_model: str = "gpt-4o-mini"
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = 3
    ai_retry_base_delay_seconds: float = 0.5
    ai_cost_per_1k_input_tokens_usd: float = 0.00015
    ai_cost_per_1k_output_tokens_usd: float = 0.0006

    # Rate limiting (token bucket: max requests per minute per client key)
    rate_limit_requests_per_minute: int = 120

    # Metrics (optional)
    metrics_enabled: bool = True

    # Fraud scoring (deterministic, non-AI)
    fraud_window_days: int = 30
    fraud_frequency_high_count: int = 5
    fraud_total_value_high_usd: float = 1500.0
    fraud_avg_order_value_high_usd: float = 300.0
    fraud_recency_hot_days: int = 3
    fraud_weight_frequency: float = 0.45
    fraud_weight_value: float = 0.35
    fraud_weight_recency: float = 0.20
    fraud_risk_medium_min: float = 0.35
    fraud_risk_high_min: float = 0.65

    # Refund engine (rule-based)
    restocking_fee_percent: float = 0.0


settings = Settings()
