from dataclasses import dataclass

from gt.auth.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class AdminRegisteredEvent(DomainEvent):
    """Event triggered when a new administrator is registered."""

    admin_id: int
    admin_uuid: str
    email: str
    full_name: str
