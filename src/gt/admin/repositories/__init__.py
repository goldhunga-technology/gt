from ._admin_repository import AdminRepository
from ._admin_role_repository import AdminRoleRepository
from ._admin_session_repository import AdminSessionRepository
from ._role_repository import RoleRepository

__all__ = [
    "AdminRepository",
    "AdminRoleRepository",
    "AdminSessionRepository",
    "RoleRepository",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
