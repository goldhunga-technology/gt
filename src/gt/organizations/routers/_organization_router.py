from fastapi import Depends, Request
from starlette.status import HTTP_400_BAD_REQUEST

from gt.auth.uow import AuthUOW
from gt.exceptions._base_exceptions import DomainException
from gt.organizations.routes import OrganizationRoutesConfig
from gt.organizations.schemas import (
    OrganizationCreateSchema,
    OrganizationResponseSchema,
    OrganizationUpdateSchema,
)
from gt.response import cr


def create_organization_router(
    *, organizations, routes: OrganizationRoutesConfig | None = None
):
    """
    Create a router for organization operations.
    """
    session_factory = organizations.session_factory
    organization_create_schema = (
        organizations.organization_create_schema or OrganizationCreateSchema
    )
    current_user = organizations.current_user
    route_config = routes or OrganizationRoutesConfig()

    from fastapi import APIRouter

    router = APIRouter()

    if route_config.is_enabled("create"):

        @router.post("/")
        async def create_organization(
            request: Request,
            body: organization_create_schema,  # type: ignore
            user=Depends(current_user),
        ):
            """
            Endpoint to create a new organization.
            """
            async with session_factory() as session:
                services = organizations.get_services(session)
                async with AuthUOW(session):
                    organization = await services.organization.create_organization(
                        name=body.name,
                        owner_id=user.id,
                        description=body.description,
                        logo=body.logo,
                    )
                    await services.member.add_member(
                        organization_id=organization.id,
                        organization_uuid=organization.uuid,
                        user_id=user.id,
                        status="active",
                        role="owner",
                    )

            return cr.success(
                data=OrganizationResponseSchema.model_validate(
                    organization
                ).model_dump(),
                message="Organization created successfully.",
            )

    if route_config.is_enabled("list"):

        @router.get("/")
        async def list_organizations(user=Depends(current_user)):
            """
            Endpoint to list all organizations owned by the current user.
            """
            async with session_factory() as session:
                organization_service = organizations.get_services(session).organization
                organizations_list = (
                    await organization_service.list_organizations_by_owner(
                        owner_id=user.id
                    )
                )

            return cr.success(
                data=[
                    OrganizationResponseSchema.model_validate(o).model_dump()
                    for o in organizations_list
                ],
                message="Organizations retrieved successfully.",
            )

    if route_config.is_enabled("get"):

        @router.get("/{slug}")
        async def get_organization(slug: str, user=Depends(current_user)):
            """
            Endpoint to retrieve an organization by its slug.
            """
            async with session_factory() as session:
                organization_service = organizations.get_services(session).organization
                organization = await organization_service.get_organization_by(slug=slug)
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

            return cr.success(
                data=OrganizationResponseSchema.model_validate(
                    organization
                ).model_dump(),
                message="Organization retrieved successfully.",
            )

    if route_config.is_enabled("update"):

        @router.patch("/{slug}")
        async def update_organization(
            slug: str,
            body: OrganizationUpdateSchema,
            user=Depends(current_user),
        ):
            """
            Endpoint to update an organization.
            """
            async with session_factory() as session:
                organization_service = organizations.get_services(session).organization
                async with AuthUOW(session):
                    organization = await organization_service.get_organization_by(
                        slug=slug
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

                    try:
                        organization = await organization_service.update_organization(
                            organization=organization,
                            name=body.name,
                            description=body.description,
                            logo=body.logo,
                            status=body.status,
                        )
                    except DomainException as e:
                        return cr.error(
                            error=e.error,
                            errors=e.errors,
                        )

            return cr.success(
                data=OrganizationResponseSchema.model_validate(
                    organization
                ).model_dump(),
                message="Organization updated successfully.",
            )

    return router
