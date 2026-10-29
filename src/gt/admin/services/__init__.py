from ._admin_service import AdminService, get_admin_service
from ._service_registry import AdminServiceRegistry

__all__ = ["AdminService", "AdminServiceRegistry", "get_admin_service"]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
