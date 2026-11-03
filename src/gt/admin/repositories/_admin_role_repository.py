from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models._admin_role_model import AdminRoleModel
from gt.admin.models._role_model import RoleModel
from gt.exceptions import CreateException


class AdminRoleRepository[
    TAdminRole: AdminRoleModel,
    TRole: RoleModel = RoleModel,
]:
    """Repository for managing administrator-role assignment persistence."""

    def __init__(
        self,
        session: AsyncSession,
        model: type[TAdminRole],
        role_model: type[TRole],
    ):
        """Initialize the repository with a database session and models.

        Args:
            session: Async SQLAlchemy session.
            model: The AdminRoleModel class.
            role_model: The RoleModel class used for joins.
        """
        self.session = session
        self.model = model
        self.role_model = role_model

    async def add(self, assignment: TAdminRole) -> TAdminRole:
        """Add a new administrator-role assignment to the database.

        Args:
            assignment: The assignment model instance to persist.

        Returns:
            The persisted assignment instance.
        """
        try:
            self.session.add(assignment)
            await self.session.flush()
            await self.session.refresh(assignment)
            return assignment
        except Exception as e:
            raise CreateException(
                error="Failed to assign role to admin in the database.",
                internal_details=str(e),
            ) from e

    async def delete(self, assignment: TAdminRole) -> None:
        """Delete an administrator-role assignment from the database.

        Args:
            assignment: The assignment model instance to delete.
        """
        try:
            await self.session.delete(assignment)
            await self.session.flush()
        except Exception as e:
            raise CreateException(
                error="Failed to revoke role from admin in the database.",
                internal_details=str(e),
            ) from e

    async def get_by(self, **kwargs) -> TAdminRole | None:
        """Retrieve an assignment by arbitrary filter criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            The matching assignment instance or None.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve admin role from the database.",
                internal_details=str(e),
            ) from e

    async def filter_by(self, **kwargs) -> list[TAdminRole]:
        """Filter assignment records by arbitrary criteria.

        Args:
            **kwargs: Filter keyword arguments passed to filter_by.

        Returns:
            A list of matching assignment instances.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to filter admin roles from the database.",
                internal_details=str(e),
            ) from e

    async def get_roles_for_admin(self, admin_id: int) -> list[TRole]:
        """Retrieve every role assigned to an administrator.

        Args:
            admin_id: The internal administrator id.

        Returns:
            A list of assigned roles.
        """
        try:
            stmt = (
                select(self.role_model)
                .select_from(self.model)
                .join(self.role_model, self.model.role_id == self.role_model.id)
                .where(self.model.admin_id == admin_id)
                .order_by(self.role_model.id)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve roles for admin from the database.",
                internal_details=str(e),
            ) from e

    async def get_roles_for_admins(
        self, admin_ids: list[int]
    ) -> dict[int, list[TRole]]:
        """Retrieve roles for several administrators in one query.

        Args:
            admin_ids: The internal administrator ids.

        Returns:
            A mapping of administrator id to their assigned roles.
        """
        if not admin_ids:
            return {}

        try:
            stmt = (
                select(self.model.admin_id, self.role_model)
                .select_from(self.model)
                .join(self.role_model, self.model.role_id == self.role_model.id)
                .where(self.model.admin_id.in_(admin_ids))
                .order_by(self.model.admin_id, self.role_model.id)
            )
            result = await self.session.execute(stmt)
            roles_by_admin: dict[int, list[TRole]] = defaultdict(list)
            for admin_id, role in result.all():
                roles_by_admin[admin_id].append(role)
            return dict(roles_by_admin)
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve roles for admins from the database.",
                internal_details=str(e),
            ) from e

    async def count_by_role_id(self, role_id: int) -> int:
        """Count the number of administrators assigned to a given role.

        Args:
            role_id: The internal role id.

        Returns:
            The total number of assignments for the role.
        """
        try:
            stmt = (
                select(func.count())
                .select_from(self.model)
                .where(self.model.role_id == role_id)
            )
            result = await self.session.execute(stmt)
            return int(result.scalar_one())
        except Exception as e:
            raise CreateException(
                error="Failed to count role assignments in the database.",
                internal_details=str(e),
            ) from e
