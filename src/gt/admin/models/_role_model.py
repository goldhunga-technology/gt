import re
import uuid
from datetime import UTC, datetime
from typing import ClassVar, TypeVar, cast

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


def generate_role_slug(name: str) -> str:
    """Generate a URL-friendly slug from a role name.

    Converts the name to lowercase, replaces whitespace with hyphens, and strips
    non-alphanumeric characters (except hyphens).

    Args:
        name: The role name to slugify.

    Returns:
        The generated slug string.
    """
    slug = name.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class RoleModel(MappedAsDataclass):
    """Represents a role that can be assigned to administrators.

    This model serves as an abstract base for role information, intended to be
    inherited by SQLModel / SQLAlchemy models in the application.

    Permissions are stored as a JSON list of string identifiers. The wildcard
    permission ``"*"`` grants every permission.
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
    description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, default=None, kw_only=True
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default_factory=list, kw_only=True
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True, kw_only=True
    )
    status: Mapped[str] = mapped_column(
        String(255), nullable=False, default="active", index=True, kw_only=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default_factory=lambda: datetime.now(UTC),
        init=False,
        kw_only=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False, kw_only=True
    )

    def is_active(self) -> bool:
        """Check if the role is active.

        Returns:
            bool: True if the role's status is 'active', False otherwise.
        """
        return self.status == "active"

    def has_permission(self, permission: str) -> bool:
        """Check whether the role grants a permission.

        Args:
            permission: The permission identifier to check.

        Returns:
            bool: True when the role has the permission or the wildcard.
        """
        return "*" in self.permissions or permission in self.permissions

    def has_any_permission(self, *permissions: str) -> bool:
        """Check whether the role grants any of the given permissions."""
        return any(self.has_permission(permission) for permission in permissions)

    def touch(self) -> None:
        """Mark the role as updated."""
        self.updated_at = datetime.now(UTC)


TRole = TypeVar("TRole", bound=RoleModel)


def create_role_model(
    base: type,
    model: type[TRole] = RoleModel,
) -> type[TRole]:
    """Create the concrete role model.

    If a custom role model is provided, it is used as the base model.
    Otherwise, ``RoleModel`` is used.

    If the model does not define ``__tablename__``, it defaults to
    ``"sys_roles"``.
    """

    attrs: dict[str, object] = {}

    if "__tablename__" not in model.__dict__:
        attrs["__tablename__"] = "sys_roles"

    cls = type(model.__name__, (base, model), attrs)
    return cast(type[TRole], cls)
