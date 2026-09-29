from typing import Any

from gt.logger import logger


class DomainException(Exception):
    """
    Custom base domain  exception
    """

    code: str = "domain_error"

    def __init__(
        self,
        error: str,
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error)
        # Domain errors are expected control flow (404/409/validation/etc.) and
        # are translated to proper HTTP responses by the global handler. Logging
        # a full stack trace on construction floods logs and can leak internal
        # details; record a concise debug line instead. Genuinely unhandled
        # errors are still logged with a trace at the handler boundary.
        logger.exception(
            "Domain exception raised: %s, internal details: %s, errors: %s",
            error,
            internal_details,
            errors,
        )
        self.error = error
        self.errors = errors


class NotFoundException(DomainException):
    """
    Custom Exception for not found
    """

    code: str = "not_found"

    def __init__(
        self,
        error: str = "Not found Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)


class CreateException(DomainException):
    """
    Custom Exception for create error
    """

    code: str = "create_error"

    def __init__(
        self,
        error: str = "Create Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)


class UpdateException(DomainException):
    """
    Custom Exception for update error
    """

    code: str = "update_error"

    def __init__(
        self,
        error: str = "Update Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)


class ConflictException(DomainException):
    """
    Custom Exception for conflict error
    """

    code: str = "conflict_error"

    def __init__(
        self,
        error: str = "Conflict Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)


class InvalidException(DomainException):
    """
    Custom Exception for invalid error
    """

    code: str = "invalid_error"

    def __init__(
        self,
        error: str = "Invalid Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)


class UnauthorizedException(DomainException):
    """
    Custom Exception for unauthorized error
    """

    code: str = "unauthorized_error"

    def __init__(
        self,
        error: str = "Unauthorized Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)


class ServerException(DomainException):
    """
    Custom Exception for server error
    """

    code: str = "server_error"

    def __init__(
        self,
        error: str = "Server Error",
        internal_details: Any | None = None,
        errors: Any | None = None,
    ):
        """Initialize with detail message and optional data."""
        super().__init__(error=error, internal_details=internal_details, errors=errors)
