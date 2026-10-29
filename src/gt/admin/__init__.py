from .admin import Admin
from .events import AdminRegisteredEvent
from .models import AdminModel, TAdmin, create_admin_model
from .repositories import AdminRepository
from .schemas import (
    AdminListQuerySchema,
    AdminListResponseSchema,
    AdminRegisterSchema,
    AdminResponseSchema,
)
from .services import AdminService, AdminServiceRegistry, get_admin_service

__all__ = [
    "Admin",
    "AdminListQuerySchema",
    "AdminListResponseSchema",
    "AdminModel",
    "AdminRegisterSchema",
    "AdminRegisteredEvent",
    "AdminRepository",
    "AdminResponseSchema",
    "AdminService",
    "AdminServiceRegistry",
    "TAdmin",
    "create_admin_model",
    "get_admin_service",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
