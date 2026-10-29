import uuid
from datetime import datetime
from typing import ClassVar, TypeVar, cast

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class AdminModel(MappedAsDataclass):
    """Represents an administrator in the application.

    This model serves as an abstract base for administrator information,
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
    email: Mapped[str] = mapped_column(
        unique=True, nullable=False, index=True, kw_only=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, kw_only=True)
    avatar_bg: Mapped[str] = mapped_column(String(255), nullable=False, kw_only=True)
    is_onboarded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, index=True, default=False, kw_only=True
    )
    status: Mapped[str] = mapped_column(
        String(255), nullable=False, default="active", index=True, kw_only=True
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False, kw_only=True
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None, kw_only=True
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None, kw_only=True
    )

    def is_active(self) -> bool:
        """Check if the administrator is active.

        Returns:
            bool: True if the administrator's status is 'active', False otherwise.
        """
        return self.status == "active"

    def is_email_verified(self) -> bool:
        """Check if the administrator's email is verified.

        Returns:
            bool: True if email_verified_at is not None, False otherwise.
        """
        return self.email_verified_at is not None


TAdmin = TypeVar("TAdmin", bound=AdminModel)


def create_admin_model(
    base: type,
    model: type[TAdmin] = AdminModel,
) -> type[TAdmin]:
    """Create the concrete admin model.

    If a custom admin model is provided, it is used as the base model.
    Otherwise, ``AdminModel`` is used.

    If the model does not define ``__tablename__``, it defaults to
    ``"sys_admins"``.
    """

    attrs: dict[str, object] = {}

    if "__tablename__" not in model.__dict__:
        attrs["__tablename__"] = "sys_admins"

    cls = type(model.__name__, (base, model), attrs)
    return cast(type[TAdmin], cls)
