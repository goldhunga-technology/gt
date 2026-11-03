from ._current_admin import current_admin
from ._require_admin_permission import require_admin_permission, require_admin_role

__all__ = [
    "current_admin",
    "require_admin_permission",
    "require_admin_role",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
