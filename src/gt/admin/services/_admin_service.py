from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.events import AdminRegisteredEvent
from gt.admin.models import AdminModel, TAdmin
from gt.admin.repositories import AdminRepository
from gt.auth.events import event_bus
from gt.auth.schemas._auth_schemas import random_avatar_color
from gt.auth.services.hash._hash_service import HasherService
from gt.exceptions import ConflictException, DomainException


class AdminService[TAdmin: AdminModel]:
    """Service for managing administrator operations."""

    def __init__(
        self,
        repository: AdminRepository[TAdmin],
        model: type[TAdmin],
        hash_service: HasherService | None = None,
    ):
        """Initialize the service with a repository and model.

        Args:
            repository: The AdminRepository instance.
            model: The AdminModel class.
            hash_service: Optional password hasher. Defaults to HasherService.
        """
        self._repository = repository
        self._model = model
        self._hash_service = hash_service or HasherService()

    async def register_admin(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        avatar_bg: str | None = None,
        status: str = "active",
        is_onboarded: bool = False,
    ) -> TAdmin:
        """Register a new administrator.

        Args:
            email: The administrator's email (stored lowercase).
            password: The plain-text password to hash.
            full_name: Optional full name; derived from the email when omitted.
            avatar_bg: Optional avatar background color.
            status: The administrator status.
            is_onboarded: Whether the administrator has completed onboarding.

        Returns:
            The created administrator instance.

        Raises:
            ConflictException: If an administrator with the same email exists.
            DomainException: On unexpected failures.
        """
        try:
            normalized_email = email.strip().lower()
            existing = await self._repository.get_by(email=normalized_email)
            if existing:
                raise ConflictException(
                    error=f"Admin with email {normalized_email} already exists.",
                    errors={"email": "This email is already registered."},
                )

            model_cls = cast("type[Any]", self._model)
            admin = model_cls(
                email=normalized_email,
                full_name=full_name or self._derive_full_name(normalized_email),
                avatar_bg=avatar_bg or random_avatar_color(),
                is_onboarded=is_onboarded,
                status=status,
                hashed_password=self._hash_service.hash(password),
            )
            created = await self._repository.add(admin)

            await event_bus.publish(
                AdminRegisteredEvent(
                    admin_id=created.id,
                    admin_uuid=created.uuid,
                    email=created.email,
                    full_name=created.full_name,
                )
            )

            return created
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to register admin.",
                internal_details=str(e),
            ) from e

    async def get_admin_by(self, **kwargs) -> TAdmin | None:
        """Retrieve an administrator by filter criteria.

        Args:
            **kwargs: Filter keyword arguments.

        Returns:
            The matching administrator instance or None.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.get_by(**kwargs)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve admin.",
                internal_details=str(e),
            ) from e

    async def list_admins(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[TAdmin], int]:
        """List administrators with pagination and optional filters.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            search: Optional case-insensitive email/full name search term.
            status: Optional status filter.

        Returns:
            A tuple of administrators and the total number of matches.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.paginate(
                limit=limit,
                offset=offset,
                search=search,
                status=status,
            )
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to list admins.",
                internal_details=str(e),
            ) from e

    @staticmethod
    def _derive_full_name(email: str) -> str:
        """Derive a display name from the email local part."""
        username = email.split("@", 1)[0]
        return username.replace(".", " ").replace("_", " ").replace("-", " ").title()


def get_admin_service(
    session: AsyncSession,
    model: type[TAdmin],
    hash_service: HasherService | None = None,
) -> AdminService[TAdmin]:
    """Factory function to create an AdminService instance.

    Args:
        session: Async SQLAlchemy session.
        model: The AdminModel class.
        hash_service: Optional password hasher.

    Returns:
        A configured AdminService.
    """
    repository = AdminRepository(session=session, model=model)
    return AdminService(
        repository=repository,
        model=model,
        hash_service=hash_service,
    )
