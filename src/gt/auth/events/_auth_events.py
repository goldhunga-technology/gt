from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """
    Base class for domain events.
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserCreatedEvent(DomainEvent):
    """
    Event triggered when a new user is created.
    """

    user_id: int
    full_name: str
    email: str
    user_uuid: str
    email_token: str
    email_token_expiry_minutes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UserEmailVerifiedEvent(DomainEvent):
    """
    Event triggered when a user's email is verified.
    """

    user_id: int
    email: str
    user_uuid: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserEmailVerificationResentEvent(DomainEvent):
    """
    Event triggered when a user's email verification token is resent.
    """

    user_id: int
    full_name: str
    email: str
    user_uuid: str
    email_token: str
    email_token_expiry_minutes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UserProfileUpdatedEvent(DomainEvent):
    """
    Event triggered when a user's profile is updated.
    """

    user_id: int
    full_name: str
    email: str
    user_uuid: str
    avatar: str | None
    avatar_bg: str
    language: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDeactivatedEvent(DomainEvent):
    """
    Event triggered when a user is deactivated.
    """

    user_id: int
    email: str
    user_uuid: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordResetRequestedEvent(DomainEvent):
    """
    Event triggered when a password reset is requested for a user.
    """

    user_id: int
    full_name: str
    email: str
    user_uuid: str
    password_reset_token: str
    password_reset_token_expiry_minutes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PasswordResetCompletedEvent(DomainEvent):
    """
    Event triggered when a user's password has been reset.
    """

    user_id: int
    email: str
    user_uuid: str
