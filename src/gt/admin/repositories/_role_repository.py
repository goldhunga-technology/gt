from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models._role_model import RoleModel
from gt.exceptions import CreateException


class RoleRepository[TRole: RoleModel]:
    """Repository for managing role persistence."""

    def __init__(self, session: AsyncSession, model: type[TRole]):
        """Initialize the repository with a database session and model.

        Args:
            session: Async SQLAlchemy session.
            model: The RoleModel class.
        """
        self.session = session
        self.model = model

    async def add(self, role: TRole) -> TRole:
        """Add a new role record to the database.

        Args:
            role: The role model instance to persist.

        Returns:
            The persisted role instance.
        """
        try:
            self.session.add(role)
            await self.session.flush()
            await self.session.refresh(role)
            return role
        except Exception as e:
            raise CreateException(
                error="Failed to add role to the database.",
                internal_details=str(e),
            ) from e

    async def update(self, role: TRole) -> TRole:
        """Update an existing role record in the database.

        Args:
            role: The role model instance to update.

        Returns:
            The updated role instance.
        """
        try:
            await self.session.flush()
            await self.session.refresh(role)
            return role
        except Exception as e:
            raise CreateException(
                error="Failed to update role in the database.",
                internal_details=str(e),
            ) from e

    async def delete(self, role: TRole) -> None:
        """Delete a role record from the database.

        Args:
            role: The role model instance to delete.
        """
        try:
            await self.session.delete(role)
            await self.session.flush()
        except Exception as e:
            raise CreateException(
                error="Failed to delete role from the database.",
                internal_details=str(e),
            ) from e

    async def get_by(self, **kwargs) -> TRole | None:
        """Retrieve a role record by arbitrary filter criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            The matching role instance or None.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve role from the database.",
                internal_details=str(e),
            ) from e

    async def filter_by(self, **kwargs) -> list[TRole]:
        """Filter role records by arbitrary criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            A list of matching role instances.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to filter roles from the database.",
                internal_details=str(e),
            ) from e

    async def paginate(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        is_system: bool | None = None,
    ) -> tuple[list[TRole], int]:
        """Retrieve a paginated list of roles and the total count.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            search: Optional case-insensitive name/slug search term.
            status: Optional status filter.
            is_system: Optional system-role filter.

        Returns:
            A tuple of matching roles and the total number of matches.
        """
        try:
            filters = []
            if search:
                pattern = f"%{search.strip()}%"
                filters.append(
                    or_(
                        self.model.name.ilike(pattern),
                        self.model.slug.ilike(pattern),
                    )
                )
            if status:
                filters.append(self.model.status == status)
            if is_system is not None:
                filters.append(self.model.is_system == is_system)

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
                error="Failed to list roles from the database.",
                internal_details=str(e),
            ) from e
