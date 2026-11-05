from enum import StrEnum
from typing import Literal

## --------------------------------  List of permissions, main list is at the bottom --------------------------------- ##
ADMIN_PERMISSIONS = [
    {
        "name": "View Admin details",
        "key": "admin.view",
        "description": "Permission to view administrator details",
        "category": "admin",
        "is_system_permission": True,
    },
    {
        "name": "Manage Admin details",
        "key": "admin.manage",
        "description": "Permission to create and edit administrator details",
        "category": "admin",
        "is_system_permission": True,
    },
    {
        "name": "Delete Admin",
        "key": "admin.delete",
        "description": "Permission to delete an administrator",
        "category": "admin",
        "is_system_permission": True,
    },
    {
        "name": "Manage Admin Roles",
        "key": "admin.manage_roles",
        "description": "Permission to assign and revoke roles for administrators",
        "category": "admin",
        "is_system_permission": True,
    },
]

ROLE_PERMISSIONS = [
    {
        "name": "View Role details",
        "key": "role.view",
        "description": "Permission to view role details",
        "category": "role",
        "is_system_permission": True,
    },
    {
        "name": "Manage Role details",
        "key": "role.manage",
        "description": "Permission to create and edit role details",
        "category": "role",
        "is_system_permission": True,
    },
    {
        "name": "Delete Role",
        "key": "role.delete",
        "description": "Permission to delete a role",
        "category": "role",
        "is_system_permission": True,
    },
]

ORGANIZATION_PERMISSIONS = [
    {
        "name": "View Organizations",
        "key": "organization.view",
        "description": "Permission to view organization details",
        "category": "organization",
        "is_system_permission": True,
    },
    {
        "name": "Manage Organizations",
        "key": "organization.manage",
        "description": "Permission to change organization status",
        "category": "organization",
        "is_system_permission": True,
    },
]


## --------------------------------  Main permissions list --------------------------------- ##
DEFAULT_PERMISSIONS = [
    {
        "name": "Allow All Permissions",
        "key": "*",
        "description": "Permission to allow all permissions",
        "category": "admin",
        "is_system_permission": True,
    },
    *ADMIN_PERMISSIONS,
    *ROLE_PERMISSIONS,
    *ORGANIZATION_PERMISSIONS,
]


## --------------------------------  Enum and literal derived from permission keys --------------------------------- ##


class PERMISSION_KEYS_ENUM(StrEnum):
    """
    Enum for all admin permission keys.
    """

    ALLOW_ALL = "*"

    ADMIN_VIEW = "admin.view"
    ADMIN_MANAGE = "admin.manage"
    ADMIN_DELETE = "admin.delete"
    ADMIN_MANAGE_ROLES = "admin.manage_roles"

    ROLE_VIEW = "role.view"
    ROLE_MANAGE = "role.manage"
    ROLE_DELETE = "role.delete"

    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_MANAGE = "organization.manage"


type PERMISSION_KEYS = Literal[
    "*",
    "admin.view",
    "admin.manage",
    "admin.delete",
    "admin.manage_roles",
    "role.view",
    "role.manage",
    "role.delete",
    "organization.view",
    "organization.manage",
]

VALID_PERMISSION_KEYS: frozenset[str] = frozenset(
    str(item["key"]) for item in DEFAULT_PERMISSIONS
)
