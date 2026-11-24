"""
Current session dependency function for retrieving the authenticated session.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.auth import Auth
from gt.auth.errors import AuthErrorCode
from gt.exceptions._base_exceptions import InvalidException


async def current_session(
    *,
    auth: Auth,
    session: AsyncSession,
    session_uuid: str,
):
    """
    Dependency function to retrieve the current authenticated session.
    """
    services = auth.get_services(session)

    user_session = await services.session.get_session_by(uuid=session_uuid)

    if not user_session or not user_session.is_active:
        raise InvalidException(
            error="Invalid or expired session.",
            errors={"code": AuthErrorCode.SESSION_INVALID},
        )

    return user_session
