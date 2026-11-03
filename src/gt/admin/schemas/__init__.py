from ._admin_schemas import (
    AdminListQuerySchema,
    AdminListResponseSchema,
    AdminLoginRequestSchema,
    AdminRegisterSchema,
    AdminResponseSchema,
)

__all__ = [
    "AdminListQuerySchema",
    "AdminListResponseSchema",
    "AdminLoginRequestSchema",
    "AdminRegisterSchema",
    "AdminResponseSchema",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
