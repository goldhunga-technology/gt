from ._admin_events import AdminRegisteredEvent

__all__ = ["AdminRegisteredEvent"]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
