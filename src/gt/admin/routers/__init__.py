from ._admin_router import create_admin_router
from ._admin_router_registry import create_admins_router
from ._role_router import create_role_router

__all__ = [
    "create_admin_router",
    "create_admins_router",
    "create_role_router",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
