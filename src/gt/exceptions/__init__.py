from ._base_exceptions import (
    ConflictException,
    CreateException,
    DomainException,
    InvalidException,
    NotFoundException,
    ServerException,
    UpdateException,
)
from ._global_exception_handlers import add_exceptions_handler

__all__ = [
    "ConflictException",
    "CreateException",
    "DomainException",
    "InvalidException",
    "NotFoundException",
    "ServerException",
    "UpdateException",
    "add_exceptions_handler",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module {__name__} has no attribute {name}")
