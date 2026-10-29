from ._admin_model import AdminModel, TAdmin, create_admin_model

__all__ = ["AdminModel", "TAdmin", "create_admin_model"]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
