from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.errors import AuthErrorCode
from gt.auth.policies import UserPolicies
from gt.exceptions._base_exceptions import DomainException, UnauthorizedException


def require_access(
    *,
    authenticated: bool = True,
    email_verified: bool = False,
    onboarded: bool = False,
    belongs_to_org: bool = False,
    auth,
):
    """
    Build a reusable access dependency for router/endpoint-level authorization.
    """

    from gt.auth.dependencies._current_user import current_user

    needs_user = authenticated or email_verified or onboarded or belongs_to_org

    async def dependency(
        request: Request,
        session: AsyncSession = Depends(auth.get_db_session),
    ):

        session_uuid = request.cookies.get("session_uuid")
        user = (
            await current_user(auth=auth, session=session, session_uuid=session_uuid)
            if session_uuid
            else None
        )

        if needs_user and user is None:
            raise UnauthorizedException(
                error="Authentication required",
                errors={"code": AuthErrorCode.UNAUTHENTICATED},
            )

        if email_verified and user is not None:
            UserPolicies.require_email_verified(user)

        if onboarded and user is not None:
            UserPolicies.require_onboarding(user)

        if belongs_to_org and user is not None:
            if auth._belongs_to_org_check is None:
                raise DomainException(
                    error="Organization is not set up.",
                    errors={"code": AuthErrorCode.ORGANIZATION_NOT_SET_UP},
                )
            await auth._belongs_to_org_check.check_user_belongs_to_organization(
                user=user, session=session
            )

        return user

    return dependency
