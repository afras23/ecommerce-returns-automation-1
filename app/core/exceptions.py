"""
Application-specific exceptions for API and service layers.

Maps to consistent HTTP responses via the global error handler.
"""


class AppError(Exception):
    """Base class for expected business or validation errors."""

    def __init__(self, message: str, *, code: str = "APP_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(AppError):
    """Resource was not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="NOT_FOUND")


class RetryableError(AppError):
    """Transient failure; caller may retry."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="RETRYABLE")


class AIProviderError(AppError):
    """AI provider returned an error or invalid response."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="AI_PROVIDER_ERROR")
