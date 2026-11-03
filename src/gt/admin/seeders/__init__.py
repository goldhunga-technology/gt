from .default_permissions import (
    ADMIN_PERMISSIONS,
    DEFAULT_PERMISSIONS,
    PERMISSION_KEYS,
    PERMISSION_KEYS_ENUM,
    ROLE_PERMISSIONS,
    VALID_PERMISSION_KEYS,
)
from .default_roles import DEFAULT_ROLES
from .default_roles_permissions import (
    DEFAULT_ROLES_PERMISSIONS,
    EVERY_ROLE_PERMISSIONS,
)

__all__ = [
    "ADMIN_PERMISSIONS",
    "DEFAULT_PERMISSIONS",
    "DEFAULT_ROLES",
    "DEFAULT_ROLES_PERMISSIONS",
    "EVERY_ROLE_PERMISSIONS",
    "PERMISSION_KEYS",
    "PERMISSION_KEYS_ENUM",
    "ROLE_PERMISSIONS",
    "VALID_PERMISSION_KEYS",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
