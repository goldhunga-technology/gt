from ._admin_router_registry import create_admins_router

__all__ = ["create_admins_router"]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
