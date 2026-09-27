from typing import Any, cast

from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from gt.auth.uow import AuthUOW
from gt.exceptions._base_exceptions import DomainException
from gt.organizations.schemas import (
    OrganizationMemberAddSchema,
    OrganizationMemberResponseSchema,
    OrganizationMemberUpdateSchema,
)
from gt.response import cr


def _get_user_service(user_service_factory, session):
    """
    Returns the auth user service used to resolve public ``user_uuid`` into
    the internal integer id, or ``None`` when not configured or when the
    service does not expose the required lookup method.
    """
    if user_service_factory is None:
        return None
    user_service = getattr(user_service_factory(session), "user", None)
    if user_service is None or not callable(getattr(user_service, "get_user_by", None)):
        return None
    return user_service


async def _resolve_user_by_uuid(user_service_factory, session, user_uuid: str):
    """
    Resolves a public user uuid to an internal user instance.

    Returns ``(user, None)`` on success or ``(None, error_response)`` when the
    user service is not configured, the lookup fails, or the uuid is unknown.
    """
    user_service = _get_user_service(user_service_factory, session)
    if user_service is None:
        return None, cr.error(
            error="User service is not configured.",
            errors={"code": "USER_SERVICE_NOT_CONFIGURED"},
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        )
    try:
        user = await user_service.get_user_by(uuid=user_uuid)
    except DomainException as e:
        return None, cr.error(error=e.error, errors=e.errors)
    if user is None:
        return None, cr.error(
            error="User not found.",
            errors={"code": "USER_NOT_FOUND"},
            status_code=HTTP_400_BAD_REQUEST,
        )
    return user, None


async def _resolve_user_uuids(user_service, members) -> dict[int, str]:
    """
    Resolves a batch of members' internal user ids to their public uuids.

    Uses a single batched query when the user service supports it and falls
    back to per-member lookups otherwise (e.g. an older installed auth
    version). Domain errors propagate to the caller for handling.
    """
    if user_service is None or not members:
        return {}

    user_ids = [m.user_id for m in members]
    batch_get = getattr(user_service, "get_users_by_ids", None)
    if callable(batch_get):
        users = await cast(Any, batch_get)(user_ids)
    else:
        users = []
        for user_id in user_ids:
            user = await user_service.get_user_by(id=user_id)
            if user is not None:
                users.append(user)
    return {user.id: str(user.uuid) for user in users}


def _member_payload(
    member, *, user_uuid: str | None, organization_uuid: str | None
) -> dict:
    """
    Builds a response payload that exposes only public uuids.
    """
    return OrganizationMemberResponseSchema(
        uuid=member.uuid,
        user_uuid=user_uuid,
        organization_uuid=organization_uuid,
        status=member.status,
        role=member.role,
    ).model_dump()


def create_organization_member_router(*, organizations):
    """
    Create a router for organization member operations.

    All externally facing identifiers are public uuids. The integer primary
    keys are resolved once at this boundary and stay internal.
    """
    session_factory = organizations.session_factory
    organization_member_add_schema = OrganizationMemberAddSchema
    current_user = organizations.current_user
    user_service_factory = organizations.user_service_factory

    router = APIRouter()

    @router.post("/{organization_slug}/members")
    async def add_member(
        organization_slug: str,
        body: organization_member_add_schema,  # type: ignore
        user=Depends(current_user),
    ):
        """
        Endpoint to add a member to an organization.

        The request body carries the public ``user_uuid``; it is resolved to
        the internal integer ``user_id`` here before calling the service.
        """
        async with session_factory() as session:
            services = organizations.get_services(session)
            organization = await services.organization.get_organization_by(
                slug=organization_slug
            )
            if not organization:
                return cr.error(
                    error="Organization not found.",
                    errors={"code": "ORGANIZATION_NOT_FOUND"},
                    status_code=HTTP_400_BAD_REQUEST,
                )
            if organization.owner_id != user.id:
                return cr.error(
                    error="You do not have access to this organization.",
                    errors={"code": "ORGANIZATION_ACCESS_DENIED"},
                )

            resolved_user, error = await _resolve_user_by_uuid(
                user_service_factory, session, str(body.user_uuid)
            )
            if error is not None:
                return error
            assert resolved_user is not None

            async with AuthUOW(session):
                try:
                    member = await services.member.add_member(
                        organization_id=organization.id,
                        organization_uuid=organization.uuid,
                        user_id=resolved_user.id,
                        status=body.status,
                        role=body.role,
                    )
                except DomainException as e:
                    return cr.error(
                        error=e.error,
                        errors=e.errors,
                    )

        return cr.success(
            data=_member_payload(
                member,
                user_uuid=str(resolved_user.uuid),
                organization_uuid=str(organization.uuid),
            ),
            message="Member added successfully.",
        )

    @router.get("/{organization_slug}/members")
    async def list_members(organization_slug: str, user=Depends(current_user)):
        """
        Endpoint to list all members of an organization.

        Members are enriched with their public uuids via a single batched
        user lookup (no N+1 query per member).
        """
        async with session_factory() as session:
            services = organizations.get_services(session)
            organization = await services.organization.get_organization_by(
                slug=organization_slug
            )
            if not organization:
                return cr.error(
                    error="Organization not found.",
                    errors={"code": "ORGANIZATION_NOT_FOUND"},
                    status_code=HTTP_400_BAD_REQUEST,
                )

            members = await services.member.list_members(
                organization_id=organization.id
            )

            try:
                user_uuid_by_id = await _resolve_user_uuids(
                    _get_user_service(user_service_factory, session), members
                )
            except DomainException as e:
                return cr.error(error=e.error, errors=e.errors)

        return cr.success(
            data=[
                _member_payload(
                    m,
                    user_uuid=user_uuid_by_id.get(m.user_id),
                    organization_uuid=str(organization.uuid),
                )
                for m in members
            ],
            message="Members retrieved successfully.",
        )

    @router.patch("/{organization_slug}/members/{member_uuid}")
    async def update_member(
        organization_slug: str,
        member_uuid: str,
        body: OrganizationMemberUpdateSchema,
        user=Depends(current_user),
    ):
        """
        Endpoint to update an organization member's status.
        """
        async with session_factory() as session:
            services = organizations.get_services(session)
            organization = await services.organization.get_organization_by(
                slug=organization_slug
            )
            if not organization:
                return cr.error(
                    error="Organization not found.",
                    errors={"code": "ORGANIZATION_NOT_FOUND"},
                    status_code=HTTP_400_BAD_REQUEST,
                )
            if organization.owner_id != user.id:
                return cr.error(
                    error="You do not have access to this organization.",
                    errors={"code": "ORGANIZATION_ACCESS_DENIED"},
                )

            async with AuthUOW(session):
                member = await services.member.get_member_by(
                    organization_id=organization.id, uuid=member_uuid
                )
                if not member:
                    return cr.error(
                        error="Member not found.",
                        errors={"code": "MEMBER_NOT_FOUND"},
                        status_code=HTTP_400_BAD_REQUEST,
                    )
                try:
                    member = await services.member.update_member(
                        member=member,
                        organization_uuid=organization.uuid,
                        status=body.status,
                        role=body.role,
                    )
                except DomainException as e:
                    return cr.error(
                        error=e.error,
                        errors=e.errors,
                    )

            member_user_uuid = None
            user_service = _get_user_service(user_service_factory, session)
            if user_service is not None:
                try:
                    member_user = await user_service.get_user_by(id=member.user_id)
                except DomainException as e:
                    return cr.error(error=e.error, errors=e.errors)
                member_user_uuid = (
                    str(member_user.uuid) if member_user is not None else None
                )

        return cr.success(
            data=_member_payload(
                member,
                user_uuid=member_user_uuid,
                organization_uuid=str(organization.uuid),
            ),
            message="Member updated successfully.",
        )

    @router.delete("/{organization_slug}/members/{member_uuid}")
    async def remove_member(
        organization_slug: str,
        member_uuid: str,
        user=Depends(current_user),
    ):
        """
        Endpoint to remove an organization member.
        """
        async with session_factory() as session:
            services = organizations.get_services(session)
            organization = await services.organization.get_organization_by(
                slug=organization_slug
            )
            if not organization:
                return cr.error(
                    error="Organization not found.",
                    errors={"code": "ORGANIZATION_NOT_FOUND"},
                    status_code=HTTP_400_BAD_REQUEST,
                )
            if organization.owner_id != user.id:
                return cr.error(
                    error="You do not have access to this organization.",
                    errors={"code": "ORGANIZATION_ACCESS_DENIED"},
                )

            async with AuthUOW(session):
                member = await services.member.get_member_by(
                    organization_id=organization.id, uuid=member_uuid
                )
                if not member:
                    return cr.error(
                        error="Member not found.",
                        errors={"code": "MEMBER_NOT_FOUND"},
                        status_code=HTTP_400_BAD_REQUEST,
                    )
                await services.member.remove_member(
                    member, organization_uuid=organization.uuid
                )

        return cr.success(message="Member removed successfully.")

    return router
