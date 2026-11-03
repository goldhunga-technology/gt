from ._admin_repository import AdminRepository, TAdmin
from ._admin_session_repository import AdminSessionRepository

__all__ = ["AdminRepository", "AdminSessionRepository", "TAdmin"]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
