from ._admin_uow import AdminUOW

__all__ = ["AdminUOW"]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
