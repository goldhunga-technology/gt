from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.dependencies._current_admin import current_admin as resolve_current_admin
from gt.admin.policies import AdminPolicy, EndpointRule
from gt.exceptions._base_exceptions import InvalidException, UnauthorizedException


def _build_require_admin_policy_dependency(policy: AdminPolicy, *, admin):
    """Create a FastAPI dependency that enforces *policy* on admin endpoints.

    The returned dependency:
    1. Matches the request ``method`` + ``path`` against the policy rules.
    2. If no rule matches (or ``required_role`` is ``None``), the endpoint is
       unrestricted by policy and proceeds without extra role checks.
    3. If a rule matches, resolves the currently authenticated administrator
       and verifies that they hold the required role (or ``superadmin`` / ``*``)
       via ``RoleService``.
    """

    async def _dependency(
        request: Request,
        session: Annotated[AsyncSession, Depends(admin.get_db_session)],
    ):
        rule: EndpointRule | None = policy.match(request.method, request.url.path)

        if rule is None or rule.required_role is None:
            return None

        session_uuid = request.cookies.get(admin.settings.session_cookie_name)
        if not session_uuid:
            raise InvalidException(
                error="Session UUID cookie is missing. Please log in again.",
                errors={"code": "SESSION_MISSING"},
            )

        current = await resolve_current_admin(
            admin=admin,
            session=session,
            session_uuid=session_uuid,
        )

        role_service = admin.get_services(session).role
        has_role = await role_service.admin_has_role(current.id, rule.required_role)
        if not has_role:
            raise UnauthorizedException(
                error="Forbidden",
                errors={"code": "ADMIN_ROLE_REQUIRED"},
            )

        return current

    return _dependency
