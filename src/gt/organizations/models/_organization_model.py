import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar, TypeVar, cast

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from gt.auth.models._auth_user_model import TUser


class OrganizationStatus(StrEnum):
    """Lifecycle status of an organization."""

    TRIAL = "trial"
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from an organization name.

    Converts the name to lowercase, replaces whitespace with hyphens,
    and strips non-alphanumeric characters (except hyphens).

    Args:
        name: The organization name to slugify.

    Returns:
        The generated slug string.
    """
    slug = name.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class OrganizationModel(MappedAsDataclass):
    """Represents an organization in the application.

    This model serves as an abstract base for organization information, intended to
    be inherited by SQLModel / SQLAlchemy models in the application.
    """

    __abstract__ = True
    __tablename__: ClassVar[str]

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, init=False, kw_only=True
    )
    uuid: Mapped[str] = mapped_column(
        unique=True,
        nullable=False,
        default_factory=lambda: str(uuid.uuid4()),
        init=False,
        kw_only=True,
    )
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, kw_only=True
    )
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, kw_only=True
    )
    owner_id: Mapped[int] = mapped_column(
        kw_only=True, nullable=False
    )  # This will be defined in the factory function
    status: Mapped[str] = mapped_column(
        String(255), nullable=False, default="active", index=True, kw_only=True
    )
    description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, default=None, kw_only=True
    )
    logo: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None, kw_only=True
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False, kw_only=True
    )
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False, kw_only=True
    )
    status_changed_by: Mapped[int | None] = mapped_column(
        nullable=True, default=None, init=False, kw_only=True
    )
    status_reason: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, default=None, init=False, kw_only=True
    )

    def effective_status(self, now: datetime | None = None) -> OrganizationStatus:
        """Return the effective status, accounting for trial expiry.

        A trial whose ``trial_ends_at`` has passed is reported as inactive
        without requiring a database write.
        """
        status = OrganizationStatus(self.status)
        if status is OrganizationStatus.TRIAL and self.trial_ends_at is not None:
            current = now or datetime.now(UTC)
            trial_ends_at = self.trial_ends_at
            if trial_ends_at.tzinfo is None:
                trial_ends_at = trial_ends_at.replace(tzinfo=UTC)
            if trial_ends_at <= current:
                return OrganizationStatus.INACTIVE
        return status

    def is_active(self) -> bool:
        """Check if the organization is usable (active or in an unexpired trial).

        Returns:
            bool: True if the effective status is 'active' or 'trial'.
        """
        return self.effective_status() in {
            OrganizationStatus.TRIAL,
            OrganizationStatus.ACTIVE,
        }


TOrganization = TypeVar("TOrganization", bound=OrganizationModel)


def create_organization_model(
    base: type,
    user_model: type[TUser],
    model: type[TOrganization] = OrganizationModel,
) -> type[TOrganization]:
    """Create the concrete organization model.

    If a custom organization model is provided, it is used as the base model.
    Otherwise, ``OrganizationModel`` is used.

    Injects the application-specific User model to establish the owner foreign key.

    If the model does not define ``__tablename__``, it defaults to
    ``"sys_organizations"``.

    Args:
        base: The declarative base class (SQLAlchemy or SQLModel).
        user_model: The concrete user model class.
        model: The organization model base to construct.

    Returns:
        The constructed OrganizationModel class.
    """

    attrs: dict[str, object] = {}

    if "__tablename__" not in model.__dict__:
        attrs["__tablename__"] = "sys_organizations"

    attrs["owner_id"] = mapped_column(
        ForeignKey(f"{user_model.__tablename__}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cls = type(model.__name__, (base, model), attrs)
    return cast(type[TOrganization], cls)
