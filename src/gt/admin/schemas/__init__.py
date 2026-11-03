from ._admin_schemas import (
    AdminListQuerySchema,
    AdminListResponseSchema,
    AdminLoginRequestSchema,
    AdminMeResponseSchema,
    AdminRegisterSchema,
    AdminResponseSchema,
)
from ._role_schemas import (
    AdminRoleAssignSchema,
    AdminRolesResponseSchema,
    PermissionResponseSchema,
    RoleCreateSchema,
    RoleListQuerySchema,
    RoleListResponseSchema,
    RoleResponseSchema,
    RoleUpdateSchema,
)

__all__ = [
    "AdminListQuerySchema",
    "AdminListResponseSchema",
    "AdminLoginRequestSchema",
    "AdminMeResponseSchema",
    "AdminRegisterSchema",
    "AdminResponseSchema",
    "AdminRoleAssignSchema",
    "AdminRolesResponseSchema",
    "PermissionResponseSchema",
    "RoleCreateSchema",
    "RoleListQuerySchema",
    "RoleListResponseSchema",
    "RoleResponseSchema",
    "RoleUpdateSchema",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
