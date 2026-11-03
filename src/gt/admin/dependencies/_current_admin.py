"""Current administrator dependency for FastAPI routes."""

from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models import AdminModel
from gt.exceptions._base_exceptions import InvalidException


async def current_admin(
    *,
    admin,
    session: AsyncSession,
    session_uuid: str,
) -> AdminModel:
    """Retrieve the current authenticated administrator.

    Raises an ``InvalidException`` when the session is missing, expired or the
    administrator no longer exists / is inactive.
    """
    services = admin.get_services(session)

    admin_session = await services.session.get_session_by(uuid=session_uuid)

    if not admin_session or not admin_session.is_active:
        raise InvalidException(
            error="Invalid or expired session.",
            errors={"code": "SESSION_INVALID"},
        )

    current = await services.admin.get_admin_by(id=admin_session.admin_id)

    if not current or not current.is_active():
        raise InvalidException(
            error="Admin is inactive or does not exist.",
            errors={"code": "ADMIN_INVALID"},
        )

    return current
