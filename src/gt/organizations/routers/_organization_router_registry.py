from gt.organizations.routes import OrganizationsRoutesConfig

from ._organization_member_router import create_organization_member_router
from ._organization_router import create_organization_router


def create_organizations_router(
    *, organizations, routes: OrganizationsRoutesConfig | None = None
):
    """
    Create a router for organization-related operations.
    """
    from fastapi import APIRouter

    config = routes or OrganizationsRoutesConfig()
    router = APIRouter(prefix="/organizations")

    organization_routes = config.resolve_organization()
    if organization_routes.any_enabled():
        router.include_router(
            create_organization_router(
                organizations=organizations,
                routes=organization_routes,
            ),
            tags=["Organizations"],
        )

    member_routes = config.resolve_member()
    if member_routes.any_enabled():
        router.include_router(
            create_organization_member_router(
                organizations=organizations,
                routes=member_routes,
            ),
            tags=["Organization Members"],
        )

    return router
