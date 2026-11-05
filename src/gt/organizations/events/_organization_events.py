from dataclasses import dataclass

from gt.auth.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationCreatedEvent(DomainEvent):
    """Event triggered when a new organization is created."""

    organization_id: int
    organization_uuid: str
    name: str
    slug: str
    owner_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationUpdatedEvent(DomainEvent):
    """Event triggered when an organization is updated."""

    organization_id: int
    organization_uuid: str
    name: str
    slug: str
    owner_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationStatusChangedEvent(DomainEvent):
    """Event triggered when an organization's status changes."""

    organization_id: int
    organization_uuid: str
    from_status: str
    to_status: str
    actor_id: int | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationDeletedEvent(DomainEvent):
    """Event triggered when an organization is deleted."""

    organization_id: int
    organization_uuid: str
    name: str
    slug: str
    owner_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationMemberAddedEvent(DomainEvent):
    """Event triggered when a member is added to an organization."""

    member_id: int
    member_uuid: str
    organization_id: int
    organization_uuid: str
    user_id: int
    status: str
    role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationMemberUpdatedEvent(DomainEvent):
    """Event triggered when an organization member is updated."""

    member_id: int
    member_uuid: str
    organization_id: int
    organization_uuid: str
    user_id: int
    status: str
    role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationMemberRemovedEvent(DomainEvent):
    """Event triggered when a member is removed from an organization."""

    member_id: int
    member_uuid: str
    organization_id: int
    organization_uuid: str
    user_id: int
