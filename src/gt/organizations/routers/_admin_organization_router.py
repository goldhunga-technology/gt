from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_400_BAD_REQUEST

from gt.admin.dependencies import require_admin_permission
from gt.admin.seeders.default_permissions import PERMISSION_KEYS_ENUM
from gt.auth.uow import AuthUOW
from gt.exceptions import DomainException
from gt.organizations.schemas import (
    AdminOrganizationListResponseSchema,
    AdminOrganizationResponseSchema,
    OrganizationResponseSchema,
    OrganizationStatsSchema,
    OrganizationStatusUpdateSchema,
)
from gt.response import cr


def create_admin_organization_router(*, organizations, admin):
    """Create the administrator router for organization operations."""
    session_factory = organizations.session_factory

    view_dependency = require_admin_permission(
        PERMISSION_KEYS_ENUM.ORGANIZATION_VIEW.value, admin=admin
    )
    manage_dependency = require_admin_permission(
        PERMISSION_KEYS_ENUM.ORGANIZATION_MANAGE.value, admin=admin
    )

    router = APIRouter(prefix="/admin/organizations")

    @router.get("")
    async def list_organizations(
        _current_admin: Annotated[Any, Depends(view_dependency)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        search: Annotated[str | None, Query(max_length=255)] = None,
        status: Annotated[str | None, Query(max_length=255)] = None,
    ):
        """List all organizations with pagination, filters and summary stats."""
        async with session_factory() as session:
            services = organizations.get_services(session)
            organization_service = services.organization
            organizations_list, total = await organization_service.list_organizations(
                limit=limit,
                offset=offset,
                search=search,
                status=status,
            )
            stats = await organization_service.get_organization_stats()
            member_counts = await services.member.count_members_by_organization_ids(
                [organization.id for organization in organizations_list]
            )

        items = [
            AdminOrganizationResponseSchema(
                **OrganizationResponseSchema.model_validate(organization).model_dump(),
                member_count=member_counts.get(organization.id, 0),
            )
            for organization in organizations_list
        ]

        return cr.success(
            data=AdminOrganizationListResponseSchema(
                items=items,
                total=total,
                limit=limit,
                offset=offset,
                stats=OrganizationStatsSchema(**stats),
            ).model_dump(),
            message="Organizations retrieved successfully.",
        )

    @router.patch("/{organization_uuid}/status")
    async def update_organization_status(
        organization_uuid: str,
        body: OrganizationStatusUpdateSchema,
        _current_admin: Annotated[Any, Depends(manage_dependency)],
    ):
        """Change an organization's status."""
        async with session_factory() as session:
            organization_service = organizations.get_services(session).organization

            async with AuthUOW(session):
                organization = await organization_service.get_organization_by(
                    uuid=organization_uuid
                )
                if not organization:
                    return cr.error(
                        error="Organization not found.",
                        errors={"code": "ORGANIZATION_NOT_FOUND"},
                        status_code=HTTP_400_BAD_REQUEST,
                    )

                try:
                    organization = await organization_service.change_status(
                        organization=organization,
                        new_status=body.status.value,
                        actor_id=_current_admin.id,
                        reason=body.reason,
                    )
                except DomainException as e:
                    return cr.error(error=e.error, errors=e.errors)

            payload = OrganizationResponseSchema.model_validate(
                organization
            ).model_dump()

        return cr.success(
            data=payload,
            message="Organization status updated successfully.",
        )

    return router
