from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.dependencies._current_admin import current_admin
from gt.admin.seeders.default_permissions import PERMISSION_KEYS
from gt.exceptions._base_exceptions import (
    UnauthorizedException,
)


def _resolve_session_uuid(request: Request, admin) -> str:
    """Read the administrator session UUID from the configured cookie."""
    session_uuid = request.cookies.get(admin.settings.session_cookie_name)
    if not session_uuid:
        raise UnauthorizedException(
            error="Authentication required.",
            errors={"code": "UNAUTHENTICATED"},
        )
    return session_uuid


def require_admin_role(*slugs: str, admin, any_of: bool = True):
    """Build an access dependency that requires the current admin to hold a role.

    Args:
        *slugs: The role slugs to check.
        admin: The configured ``Admin`` instance.
        any_of: When True (default), any of the roles is sufficient; otherwise
            every role is required.
    """

    async def dependency(
        request: Request,
        session: Annotated[AsyncSession, Depends(admin.get_db_session)],
    ):
        session_uuid = _resolve_session_uuid(request, admin)
        current = await current_admin(
            admin=admin, session=session, session_uuid=session_uuid
        )
        role_service = admin.get_services(session).role

        results = [
            await role_service.admin_has_role(current.id, slug) for slug in slugs
        ]
        allowed = any(results) if any_of else all(results)
        if not allowed:
            raise UnauthorizedException(
                error="You do not have the required role.",
                errors={"code": "ROLE_REQUIRED"},
            )

        return current

    return dependency


def require_admin_permission(
    *permissions: PERMISSION_KEYS | str,
    admin,
    any_of: bool = True,
):
    """Build an access dependency that requires admin permissions.

    Args:
        *permissions: The permission identifiers to check.
        admin: The configured ``Admin`` instance.
        any_of: When True (default), any of the permissions is sufficient;
            otherwise every permission is required.
    """

    async def dependency(
        request: Request,
        session: Annotated[AsyncSession, Depends(admin.get_db_session)],
    ):
        session_uuid = _resolve_session_uuid(request, admin)
        current = await current_admin(
            admin=admin, session=session, session_uuid=session_uuid
        )
        role_service = admin.get_services(session).role

        results = [
            await role_service.admin_has_permission(current.id, str(permission))
            for permission in permissions
        ]
        allowed = any(results) if any_of else all(results)
        if not allowed:
            raise UnauthorizedException(
                error="You do not have the required permission.",
                errors={"code": "PERMISSION_DENIED"},
            )

        return current

    return dependency
