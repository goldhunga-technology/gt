from ._admin_model import AdminModel, TAdmin, create_admin_model
from ._admin_role_model import (
    AdminRoleModel,
    TAdminRole,
    create_admin_role_model,
)
from ._admin_session_model import (
    AdminSessionModelBase,
    TAdminSession,
    create_admin_session_model,
)
from ._role_model import RoleModel, TRole, create_role_model, generate_role_slug

__all__ = [
    "AdminModel",
    "AdminRoleModel",
    "AdminSessionModelBase",
    "RoleModel",
    "TAdmin",
    "TAdminRole",
    "TAdminSession",
    "TRole",
    "create_admin_model",
    "create_admin_role_model",
    "create_admin_session_model",
    "create_role_model",
    "generate_role_slug",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
