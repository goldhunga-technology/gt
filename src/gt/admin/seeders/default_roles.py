DEFAULT_ROLES = [
    {
        "name": "superadmin",
        "slug": "superadmin",
        "description": "Superadmin role with full access to all resources and permissions.",
        "is_system": True,
    },
    {
        "name": "admin",
        "slug": "admin",
        "description": "Admin role with elevated permissions to manage administrators and roles.",
        "is_system": True,
    },
    {
        "name": "viewer",
        "slug": "viewer",
        "description": "Viewer role with read-only access to administrator resources.",
        "is_system": True,
    },
]
