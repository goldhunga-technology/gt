"""
Current user dependency for FastAPI routes. This module provides a function to retrieve the current authenticated user based on the provided session uuid.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.auth import Auth
from gt.auth.errors import AuthErrorCode
from gt.auth.models._auth_user_model import AuthUserModel
from gt.exceptions._base_exceptions import InvalidException


async def current_user(
    *,
    auth: Auth,
    session: AsyncSession,
    session_uuid: str,
) -> AuthUserModel:
    """
    Dependency function to retrieve the current authenticated user.

    Returns:
        The current authenticated user object if the session is valid, otherwise raises an HTTPException.
    """

    services = auth.get_services(session)

    user_session = await services.session.get_session_by(uuid=session_uuid)

    if not user_session or not user_session.is_active:
        raise InvalidException(
            error="Invalid or expired session.",
            errors={"code": AuthErrorCode.SESSION_INVALID},
        )

    user = await services.user.get_user_by(id=user_session.user_id)

    if not user or not user.is_active():
        raise InvalidException(
            error="User is inactive or does not exist.",
            errors={"code": AuthErrorCode.USER_INVALID},
        )

    return user
