import uuid
from datetime import UTC, datetime
from typing import ClassVar, TypeVar, cast

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from gt.admin.models._admin_model import TAdmin
from gt.admin.models._role_model import TRole


class AdminRoleModel(MappedAsDataclass):
    """Represents the assignment of a role to an administrator.

    This model serves as an abstract base for administrator-role assignments,
    intended to be inherited by SQLModel / SQLAlchemy models in the application.
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
    admin_id: Mapped[int] = mapped_column(
        kw_only=True, nullable=False
    )  # This will be defined in the factory function
    role_id: Mapped[int] = mapped_column(
        kw_only=True, nullable=False
    )  # This will be defined in the factory function
    assigned_by: Mapped[int | None] = mapped_column(
        nullable=True, default=None, kw_only=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default_factory=lambda: datetime.now(UTC),
        init=False,
        kw_only=True,
    )


TAdminRole = TypeVar("TAdminRole", bound=AdminRoleModel)


def create_admin_role_model(
    base: type,
    admin_model: type[TAdmin],
    role_model: type[TRole],
    model: type[TAdminRole] = AdminRoleModel,
) -> type[TAdminRole]:
    """Create the concrete administrator-role assignment model.

    Injects the application-specific base, Admin and Role models to establish
    relationships and avoid circular dependencies.

    If the model does not define ``__tablename__``, it defaults to
    ``"sys_admin_roles"``.

    Args:
        base: The declarative base class (SQLAlchemy or SQLModel).
        admin_model: The concrete administrator model class.
        role_model: The concrete role model class.
        model: The administrator-role model base to construct.

    Returns:
        The constructed AdminRoleModel class.
    """

    attrs: dict[str, object] = {}

    if "__tablename__" not in model.__dict__:
        attrs["__tablename__"] = "sys_admin_roles"

    attrs["admin_id"] = mapped_column(
        ForeignKey(f"{admin_model.__tablename__}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attrs["role_id"] = mapped_column(
        ForeignKey(f"{role_model.__tablename__}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attrs["assigned_by"] = mapped_column(
        ForeignKey(f"{admin_model.__tablename__}.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )
    attrs["__table_args__"] = (
        UniqueConstraint("admin_id", "role_id", name="uq_sys_admin_roles_admin_role"),
    )

    cls = type(model.__name__, (base, model), attrs)
    return cast(type[TAdminRole], cls)
