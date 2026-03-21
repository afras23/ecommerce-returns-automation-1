from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./returns.db"

    # Return policy
    return_window_days: int = 30

    # Decision thresholds
    refund_threshold_amount: float = 500.0
    high_value_manual_review: bool = True

    # Restricted product types (e.g. ["digital", "perishable"])
    restricted_product_types: List[str] = []

    model_config = {"env_file": ".env"}


settings = Settings()
