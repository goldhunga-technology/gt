from enum import StrEnum

from gt.auth.errors import AuthErrorCode


class AdminErrorCode(StrEnum):
    """Centralized error codes for administrator-specific errors.

    Shared authentication and session error codes (such as ``SESSION_INVALID``
    and ``UNAUTHENTICATED``) live in :class:`gt.auth.AuthErrorCode` and are
    reused directly across the admin module for consistency.
    """

    ADMIN_INVALID = "ADMIN_INVALID"
    ADMIN_INACTIVE = "ADMIN_INACTIVE"
    ADMIN_AUTH_NOT_CONFIGURED = "ADMIN_AUTH_NOT_CONFIGURED"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"


__all__ = ["AdminErrorCode", "AuthErrorCode"]
