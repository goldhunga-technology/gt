from gt.admin.seeders.default_permissions import PERMISSION_KEYS_ENUM

EVERY_ROLE_PERMISSIONS = [
    PERMISSION_KEYS_ENUM.ADMIN_VIEW.value,
    PERMISSION_KEYS_ENUM.ROLE_VIEW.value,
]

## ------------------------------------ Main Default role permissions ------------------------------------ ##

DEFAULT_ROLES_PERMISSIONS: dict[str, list[str]] = {
    "superadmin": ["*"],
    "admin": [
        PERMISSION_KEYS_ENUM.ADMIN_VIEW.value,
        PERMISSION_KEYS_ENUM.ADMIN_MANAGE.value,
        PERMISSION_KEYS_ENUM.ADMIN_DELETE.value,
        PERMISSION_KEYS_ENUM.ADMIN_MANAGE_ROLES.value,
        PERMISSION_KEYS_ENUM.ROLE_VIEW.value,
        PERMISSION_KEYS_ENUM.ROLE_MANAGE.value,
        PERMISSION_KEYS_ENUM.ROLE_DELETE.value,
    ],
    "viewer": [],
}

## adding every role permissions to all roles except superadmin
for role, permissions in DEFAULT_ROLES_PERMISSIONS.items():
    if role != "superadmin":
        DEFAULT_ROLES_PERMISSIONS[role] = list(
            dict.fromkeys(permissions + EVERY_ROLE_PERMISSIONS)
        )
