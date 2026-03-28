"""
Unified application exceptions.

All services should raise subclasses of AppError instead of returning
{"error": ...} dicts. A single FastAPI exception handler in main.py
converts these to proper HTTP responses.
"""


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class ConflictError(AppError):
    """Duplicate or conflicting resource (409)."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class ValidationError(AppError):
    """Business-logic validation failure (400)."""
    pass


class ExternalServiceError(AppError):
    """An external API call failed after retries (502)."""

    def __init__(self, service: str, detail: str = ""):
        msg = f"{service} service unavailable"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, status_code=502)
