"""
Request-scoped context (correlation IDs) using context variables.
"""

from contextvars import ContextVar

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
