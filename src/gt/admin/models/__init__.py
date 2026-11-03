from ._admin_model import AdminModel, TAdmin, create_admin_model
from ._admin_session_model import (
    AdminSessionModelBase,
    TAdminSession,
    create_admin_session_model,
)

__all__ = [
    "AdminModel",
    "AdminSessionModelBase",
    "TAdmin",
    "TAdminSession",
    "create_admin_model",
    "create_admin_session_model",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
