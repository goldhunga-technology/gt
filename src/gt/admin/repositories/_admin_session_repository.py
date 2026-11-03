from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models._admin_session_model import AdminSessionModelBase
from gt.exceptions import CreateException

TAdminSession = TypeVar("TAdminSession", bound=AdminSessionModelBase)


class AdminSessionRepository[TAdminSession: AdminSessionModelBase]:
    """Repository for managing administrator session persistence."""

    def __init__(self, session: AsyncSession, model: type[TAdminSession]):
        """Initialize the repository with a database session and model.

        Args:
            session: Async SQLAlchemy session.
            model: The AdminSessionModel class.
        """
        self.session = session
        self.model = model

    async def add(self, session_record: TAdminSession) -> TAdminSession:
        """Add a new session record to the database.

        Args:
            session_record: The session model instance to persist.

        Returns:
            The persisted session instance.
        """
        try:
            self.session.add(session_record)
            await self.session.flush()
            await self.session.refresh(session_record)
            return session_record
        except Exception as e:
            raise CreateException(
                error="Failed to add admin session to the database.",
                internal_details=str(e),
            ) from e

    async def get_by(self, **kwargs) -> TAdminSession | None:
        """Retrieve a session record by arbitrary filter criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            The matching session instance or None.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve admin session from the database.",
                internal_details=str(e),
            ) from e

    async def update(self, session_record: TAdminSession) -> TAdminSession:
        """Update an existing session record in the database.

        Args:
            session_record: The session model instance to update.

        Returns:
            The updated session instance.
        """
        try:
            await self.session.flush()
            await self.session.refresh(session_record)
            return session_record
        except Exception as e:
            raise CreateException(
                error="Failed to update admin session in the database.",
                internal_details=str(e),
            ) from e

    async def filter_by(self, **kwargs) -> list[TAdminSession]:
        """Filter session records by arbitrary criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            A list of matching session instances.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to filter admin sessions from the database.",
                internal_details=str(e),
            ) from e
