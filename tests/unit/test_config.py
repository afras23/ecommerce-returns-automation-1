"""
Tests for Pydantic settings loading.
"""

import pytest
from app.config import settings


def test_settings_loads_with_defaults() -> None:
    assert settings.database_url
    assert settings.return_window_days >= 1
    assert 0.0 < settings.auto_approve_score <= 1.0
    assert settings.ai_provider in ("mock", "openai", "openai_compatible")


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import Settings

    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    fresh = Settings()
    assert fresh.log_level == "WARNING"
