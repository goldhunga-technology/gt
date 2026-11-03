from datetime import UTC, datetime, timedelta
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models._admin_session_model import AdminSessionModelBase
from gt.admin.repositories._admin_session_repository import AdminSessionRepository
from gt.exceptions import DomainException

TAdminSession = TypeVar("TAdminSession", bound=AdminSessionModelBase)


class AdminSessionService[TAdminSession: AdminSessionModelBase]:
    """Service for managing administrator session operations."""

    def __init__(
        self,
        repository: AdminSessionRepository[TAdminSession],
        model: type[TAdminSession],
    ):
        """Initialize the service with a repository and model.

        Args:
            repository: The AdminSessionRepository instance.
            model: The AdminSessionModel class.
        """
        self._repository = repository
        self._model = model

    async def create_session(
        self,
        admin_id: int,
        expire_minutes: int,
        device: str,
        ip_address: str,
        browser: str,
    ) -> TAdminSession:
        """Create a new administrator session.

        Args:
            admin_id: The ID of the administrator.
            expire_minutes: How long the session stays valid.
            device: The device that created the session.
            ip_address: The IP address that created the session.
            browser: The browser that created the session.

        Returns:
            The created session instance.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            session = self._model(
                admin_id=admin_id,
                expires_at=datetime.now(UTC) + timedelta(minutes=expire_minutes),
                device=device,
                ip_address=ip_address,
                browser=browser,
            )
            return await self._repository.add(session)

        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to create admin session.",
                internal_details=str(e),
            ) from e

    async def get_session_by(self, **kwargs) -> TAdminSession | None:
        """Retrieve a session by filter criteria.

        Args:
            **kwargs: Filter keyword arguments.

        Returns:
            The matching session instance or None.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.get_by(**kwargs)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve admin session.",
                internal_details=str(e),
            ) from e

    async def invalidate_session(self, session_uuid: str) -> None:
        """Invalidate a session by its UUID.

        Args:
            session_uuid: The UUID of the session to invalidate.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            session = await self.get_session_by(uuid=session_uuid)
            if not session:
                raise DomainException(
                    error="Session not found.",
                    internal_details=f"No admin session found with uuid: {session_uuid}",
                )
            if not session.is_active:
                raise DomainException(
                    error="Session is already inactive.",
                    internal_details=f"Admin session with uuid: {session_uuid} is already inactive.",
                )

            session.revoke()
            await self._repository.update(session)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to invalidate admin session.",
                internal_details=str(e),
            ) from e


def get_admin_session_service(
    session: AsyncSession, model: type[TAdminSession]
) -> AdminSessionService[TAdminSession]:
    """Factory function to create an AdminSessionService instance.

    Args:
        session: Async SQLAlchemy session.
        model: The AdminSessionModel class.

    Returns:
        A configured AdminSessionService.
    """
    repository = AdminSessionRepository(session=session, model=model)
    return AdminSessionService(repository=repository, model=model)
