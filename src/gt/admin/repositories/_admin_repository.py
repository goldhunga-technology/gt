from typing import TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models import AdminModel
from gt.exceptions import CreateException

TAdmin = TypeVar("TAdmin", bound=AdminModel)


class AdminRepository[TAdmin: AdminModel]:
    """Repository for managing administrator persistence."""

    def __init__(self, session: AsyncSession, model: type[TAdmin]):
        """Initialize the repository with a database session and model.

        Args:
            session: Async SQLAlchemy session.
            model: The AdminModel class.
        """
        self.session = session
        self.model = model

    async def add(self, admin: TAdmin) -> TAdmin:
        """Add a new administrator record to the database.

        Args:
            admin: The administrator model instance to persist.

        Returns:
            The persisted administrator instance.
        """
        try:
            self.session.add(admin)
            await self.session.flush()
            await self.session.refresh(admin)
            return admin
        except Exception as e:
            raise CreateException(
                error="Failed to add admin to the database.",
                internal_details=str(e),
            ) from e

    async def update(self, admin: TAdmin) -> TAdmin:
        """Update an existing administrator record in the database.

        Args:
            admin: The administrator model instance to update.

        Returns:
            The updated administrator instance.
        """
        try:
            await self.session.flush()
            await self.session.refresh(admin)
            return admin
        except Exception as e:
            raise CreateException(
                error="Failed to update admin in the database.",
                internal_details=str(e),
            ) from e

    async def get_by(self, **kwargs) -> TAdmin | None:
        """Retrieve an administrator record by arbitrary filter criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            The matching administrator instance or None.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve admin from the database.",
                internal_details=str(e),
            ) from e

    async def filter_by(self, **kwargs) -> list[TAdmin]:
        """Filter administrator records by arbitrary criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            A list of matching administrator instances.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to filter admins from the database.",
                internal_details=str(e),
            ) from e

    async def paginate(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[TAdmin], int]:
        """Retrieve a paginated list of administrators and the total count.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            search: Optional case-insensitive email/full name search term.
            status: Optional status filter.

        Returns:
            A tuple of matching administrators and the total number of matches.
        """
        try:
            filters = []
            if search:
                pattern = f"%{search.strip()}%"
                filters.append(
                    or_(
                        self.model.email.ilike(pattern),
                        self.model.full_name.ilike(pattern),
                    )
                )
            if status:
                filters.append(self.model.status == status)

            stmt = select(self.model)
            count_stmt = select(func.count()).select_from(self.model)
            if filters:
                stmt = stmt.where(*filters)
                count_stmt = count_stmt.where(*filters)

            stmt = stmt.order_by(self.model.id).limit(limit).offset(offset)
            result = await self.session.execute(stmt)
            total_result = await self.session.execute(count_stmt)
            return list(result.scalars().all()), int(total_result.scalar_one())
        except Exception as e:
            raise CreateException(
                error="Failed to list admins from the database.",
                internal_details=str(e),
            ) from e
