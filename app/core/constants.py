"""
Application-wide constants not driven by environment configuration.

Prefer `app.config.settings` for tunable values.
"""

# HTTP / API
DEFAULT_API_PREFIX = "/api/v1"

# Rate limiting (fallback when settings not injected in tests)
DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE = 120
