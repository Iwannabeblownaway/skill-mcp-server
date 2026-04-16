"""
Custom exception classes for the application.

Provides standardized exception types for common error scenarios.
"""


class ApplicationException(Exception):
    """Base exception for all application exceptions."""

    def __init__(self, message: str = "An application error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class NotFound(ApplicationException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str = "Resource", identifier: str = "") -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message)


class Forbidden(ApplicationException):
    """Raised when access to a resource is forbidden."""

    def __init__(self, message: str = "Access to this resource is forbidden") -> None:
        super().__init__(message)


class Unauthorized(ApplicationException):
    """Raised when authentication is required but not provided or invalid."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


class ValidationError(ApplicationException):
    """Raised when input validation fails."""

    def __init__(self, field: str = "", message: str = "Validation failed") -> None:
        if field:
            message = f"Validation error for '{field}': {message}"
        super().__init__(message)


class Conflict(ApplicationException):
    """Raised when there's a conflict with the current state."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message)
