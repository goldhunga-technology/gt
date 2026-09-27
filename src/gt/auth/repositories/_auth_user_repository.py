from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.models import AuthUserModel
from gt.exceptions import CreateException


class AuthUserRepository[TUser: AuthUserModel]:
    """
    Auth user repository class for managing user authentication and related operations.
    """

    def __init__(self, session: AsyncSession, model: type[TUser]):
        """
        Initialize the AuthUserRepository with a database session and a model.
        """

        self.session = session
        self.model = model

    async def add(self, user: TUser) -> TUser:
        """
        Add a new user to the database.
        """
        try:
            self.session.add(user)
            await self.session.flush()
            await self.session.refresh(user)
            return user
        except Exception as e:
            raise CreateException(
                error="Failed to add user to the database.",
                internal_details=str(e),
            ) from e

    async def update(self, user: TUser) -> TUser:
        """
        Update an existing user in the database.
        """
        try:
            await self.session.flush()
            await self.session.refresh(user)
            return user
        except Exception as e:
            raise CreateException(
                error="Failed to update user in the database.",
                internal_details=str(e),
            ) from e

    async def get_by(self, **kwargs) -> TUser | None:
        """
        Retrieve a user from the database based on provided keyword arguments.
        """
        try:
            stmt = select(self.model).filter_by(**kwargs)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve user from the database.",
                internal_details=str(e),
            ) from e

    async def get_by_ids(self, ids: list[int]) -> list[TUser]:
        """
        Retrieve multiple users by their internal integer ids in a single query.
        """
        if not ids:
            return []
        try:
            stmt = select(self.model).where(self.model.id.in_(ids))
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            raise CreateException(
                error="Failed to retrieve users from the database.",
                internal_details=str(e),
            ) from e
