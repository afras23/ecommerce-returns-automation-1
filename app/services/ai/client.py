"""
Production-oriented async AI client with retries, cost/latency tracking, and structured logs.

Supports mock mode for tests and local development without external calls.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import TYPE_CHECKING, Any

import httpx

from app.core.context import correlation_id_ctx
from app.core.exceptions import AIProviderError, RetryableError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AICallResult:
    """Outcome of a single AI completion call."""

    content: str
    tokens_used: int
    cost_usd: float
    latency_ms: float


class _DailyCostAccumulator:
    """Thread-safe per-UTC-day total spend in USD."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._day = date.today()
        self._total_usd = 0.0

    def add(self, amount_usd: float) -> float:
        with self._lock:
            today = date.today()
            if today != self._day:
                self._day = today
                self._total_usd = 0.0
            self._total_usd += amount_usd
            return self._total_usd


@dataclass
class AIClient:
    """
    Async AI client with exponential backoff, token/cost accounting, and latency measurement.

    When ``ai_provider`` is ``mock``, returns deterministic content without HTTP.
    """

    settings: Any  # Settings — Any avoids circular import in type checkers
    _daily_cost: _DailyCostAccumulator = field(default_factory=_DailyCostAccumulator, repr=False)

    def _estimate_cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        inp = (prompt_tokens / 1000.0) * self.settings.ai_cost_per_1k_input_tokens_usd
        out = (completion_tokens / 1000.0) * self.settings.ai_cost_per_1k_output_tokens_usd
        return float(round(inp + out, 8))

    async def complete(
        self,
        *,
        user_message: str,
        system_message: str | None = None,
        model: str | None = None,
    ) -> AICallResult:
        """
        Run a chat completion and return structured metrics.

        Args:
            user_message: Primary user content.
            system_message: Optional system prompt.
            model: Override configured model when set.

        Returns:
            AICallResult with text, tokens, cost, and latency.

        Raises:
            AIProviderError: On non-retryable provider errors.
            RetryableError: When retries are exhausted for transient failures.
        """
        use_model = model or self.settings.ai_model
        if self.settings.ai_provider == "mock":
            return await self._mock_complete(user_message, use_model)

        last_error: BaseException | None = None
        delay = self.settings.ai_retry_base_delay_seconds
        max_retries = max(1, int(self.settings.ai_max_retries))

        for attempt in range(1, max_retries + 1):
            try:
                return await self._http_complete(
                    user_message=user_message,
                    system_message=system_message,
                    model=use_model,
                    attempt=attempt,
                )
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                    code = exc.response.status_code
                    if 400 <= code < 500 and code != 429:
                        raise AIProviderError(f"AI provider client error: {code}") from exc
                    if code < 500 and code != 429:
                        raise AIProviderError(f"AI provider rejected request: {code}") from exc

                if attempt >= max_retries:
                    logger.warning(
                        "ai_call_failed_after_retries",
                        extra={
                            "correlation_id": correlation_id_ctx.get(),
                            "attempt": attempt,
                            "provider": self.settings.ai_provider,
                            "model": use_model,
                            "error": str(exc),
                        },
                    )
                    raise RetryableError("AI provider unavailable after retries") from exc

                jitter = random.uniform(0, delay * 0.25)
                sleep_s = delay + jitter
                logger.warning(
                    "ai_call_retry",
                    extra={
                        "correlation_id": correlation_id_ctx.get(),
                        "attempt": attempt,
                        "sleep_seconds": round(sleep_s, 3),
                        "provider": self.settings.ai_provider,
                    },
                )
                await asyncio.sleep(sleep_s)
                delay *= 2

        assert last_error is not None
        raise RetryableError("AI call failed") from last_error

    async def _mock_complete(self, user_message: str, model: str) -> AICallResult:
        start = time.perf_counter()
        content = f"[mock] {model}: processed {len(user_message)} chars"
        tokens_used = max(1, len(user_message) // 4)
        cost = self._estimate_cost_usd(tokens_used // 2, tokens_used // 2)
        daily = self._daily_cost.add(cost)
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "ai_call_mock",
            extra={
                "correlation_id": correlation_id_ctx.get(),
                "model": model,
                "tokens_used": tokens_used,
                "cost_usd": cost,
                "daily_cost_usd": daily,
                "latency_ms": round(latency_ms, 3),
            },
        )
        return AICallResult(
            content=content,
            tokens_used=tokens_used,
            cost_usd=cost,
            latency_ms=round(latency_ms, 3),
        )

    async def _http_complete(
        self,
        *,
        user_message: str,
        system_message: str | None,
        model: str,
        attempt: int,
    ) -> AICallResult:
        if not self.settings.ai_api_key:
            raise AIProviderError("AI_API_KEY is not set for non-mock provider")

        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        url = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.settings.ai_timeout_seconds) as http:
            response = await http.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.perf_counter() - start) * 1000
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
        cost = self._estimate_cost_usd(prompt_tokens, completion_tokens)
        daily = self._daily_cost.add(cost)

        logger.info(
            "ai_call_complete",
            extra={
                "correlation_id": correlation_id_ctx.get(),
                "attempt": attempt,
                "provider": self.settings.ai_provider,
                "model": model,
                "tokens_used": total_tokens,
                "cost_usd": cost,
                "daily_cost_usd": daily,
                "latency_ms": round(latency_ms, 3),
            },
        )

        return AICallResult(
            content=str(content),
            tokens_used=total_tokens,
            cost_usd=cost,
            latency_ms=round(latency_ms, 3),
        )
