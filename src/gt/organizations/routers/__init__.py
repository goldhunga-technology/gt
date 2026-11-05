from ._admin_organization_router import create_admin_organization_router
from ._organization_router_registry import create_organizations_router

__all__ = [
    "create_admin_organization_router",
    "create_organizations_router",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
