from .admin import Admin
from .events import AdminRegisteredEvent
from .models import (
    AdminModel,
    AdminSessionModelBase,
    TAdmin,
    TAdminSession,
    create_admin_model,
    create_admin_session_model,
)
from .repositories import AdminRepository, AdminSessionRepository
from .schemas import (
    AdminListQuerySchema,
    AdminListResponseSchema,
    AdminLoginRequestSchema,
    AdminRegisterSchema,
    AdminResponseSchema,
)
from .services import (
    AdminLoginService,
    AdminService,
    AdminServiceRegistry,
    AdminSessionService,
    get_admin_login_service,
    get_admin_service,
    get_admin_session_service,
)
from .settings import AdminSettings
from .uow import AdminUOW

__all__ = [
    "Admin",
    "AdminListQuerySchema",
    "AdminListResponseSchema",
    "AdminLoginRequestSchema",
    "AdminLoginService",
    "AdminModel",
    "AdminRegisterSchema",
    "AdminRegisteredEvent",
    "AdminRepository",
    "AdminResponseSchema",
    "AdminService",
    "AdminServiceRegistry",
    "AdminSessionModelBase",
    "AdminSessionRepository",
    "AdminSessionService",
    "AdminSettings",
    "AdminUOW",
    "TAdmin",
    "TAdminSession",
    "create_admin_model",
    "create_admin_session_model",
    "get_admin_login_service",
    "get_admin_service",
    "get_admin_session_service",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
