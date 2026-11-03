from ._admin_login_service import AdminLoginService, get_admin_login_service
from ._admin_service import AdminService, get_admin_service
from ._admin_session_service import AdminSessionService, get_admin_session_service
from ._role_service import RoleService, get_role_service
from ._service_registry import AdminServiceRegistry

__all__ = [
    "AdminLoginService",
    "AdminService",
    "AdminServiceRegistry",
    "AdminSessionService",
    "RoleService",
    "get_admin_login_service",
    "get_admin_service",
    "get_admin_session_service",
    "get_role_service",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
