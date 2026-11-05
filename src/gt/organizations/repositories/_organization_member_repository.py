from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gt.exceptions import CreateException
from gt.organizations.models import OrganizationMemberModelBase

TOrganizationMember = TypeVar("TOrganizationMember", bound=OrganizationMemberModelBase)


class OrganizationMemberRepository[TOrganizationMember: OrganizationMemberModelBase]:
    """Repository for managing organization member persistence."""

    def __init__(self, session: AsyncSession, model: type[TOrganizationMember]):
        """Initialize the repository with a database session and model.

        Args:
            session: Async SQLAlchemy session.
            model: The OrganizationMemberModel class.
        """
        self.session = session
        self.model = model

    async def add(self, member: TOrganizationMember) -> TOrganizationMember:
        """Add a new organization member record to the database.

        Args:
            member: The organization member model instance to persist.

        Returns:
            The persisted organization member instance.
        """
        try:
            self.session.add(member)
            await self.session.flush()
            await self.session.refresh(member)
            return member
        except Exception as e:
            raise CreateException(
                error="Failed to add organization member to the database.",
                internal_details=str(e),
            ) from e

    async def get_by(self, **kwargs) -> TOrganizationMember | None:
        """Retrieve an organization member record by filter criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            The matching organization member instance or None.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve organization member from the database.",
                internal_details=str(e),
            ) from e

    async def update(self, member: TOrganizationMember) -> TOrganizationMember:
        """Update an existing organization member record in the database.

        Args:
            member: The organization member model instance to update.

        Returns:
            The updated organization member instance.
        """
        try:
            await self.session.flush()
            await self.session.refresh(member)
            return member
        except Exception as e:
            raise CreateException(
                error="Failed to update organization member in the database.",
                internal_details=str(e),
            ) from e

    async def filter_by(self, **kwargs) -> list[TOrganizationMember]:
        """Filter organization member records by arbitrary criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            A list of matching organization member instances.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to filter organization members from the database.",
                internal_details=str(e),
            ) from e

    async def count_by_organization_ids(
        self, organization_ids: list[int]
    ) -> dict[int, int]:
        """Return member counts keyed by organization id."""
        if not organization_ids:
            return {}
        try:
            stmt = (
                select(self.model.organization_id, func.count())
                .where(self.model.organization_id.in_(organization_ids))
                .group_by(self.model.organization_id)
            )
            result = await self.session.execute(stmt)
            return {
                int(organization_id): int(count)
                for organization_id, count in result.all()
            }
        except Exception as e:
            raise CreateException(
                error="Failed to count organization members.",
                internal_details=str(e),
            ) from e

    async def delete(self, member: TOrganizationMember) -> None:
        """Delete an organization member record from the database.

        Args:
            member: The organization member model instance to delete.
        """
        try:
            await self.session.delete(member)
            await self.session.flush()
        except Exception as e:
            raise CreateException(
                error="Failed to delete organization member from the database.",
                internal_details=str(e),
            ) from e
