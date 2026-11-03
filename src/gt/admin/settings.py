from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True, frozen=True, kw_only=True)
class AdminSettings:
    """
    Configuration settings for the administrator authentication system.

    These settings are supplied from outside the package via
    ``Admin(settings=AdminSettings(...))`` so hosts control cookie behaviour
    and session lifetime just like ``AuthSettings`` does for auth users.
    """

    ## cookie settings
    cookie_domain: str | None = None
    cookie_path: str = "/"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_name: str = "admin_session_uuid"

    session_expiration_minutes: int = 60 * 24 * 7  # 7 days
