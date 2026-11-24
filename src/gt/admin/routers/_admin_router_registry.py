from gt.admin.routes import AdminRoutesConfig

from ._admin_router import create_admin_router
from ._role_router import create_role_router


def create_admins_router(*, admin, routes: AdminRoutesConfig | None = None):
    """
    Create a router for admin-related operations.
    """
    from fastapi import APIRouter

    config = routes or AdminRoutesConfig()
    router = APIRouter(prefix="/admin")

    admin_routes = config.resolve_admin()
    if admin_routes.any_enabled():
        router.include_router(
            create_admin_router(admin=admin, routes=admin_routes),
            tags=["Admin"],
        )

    role_routes = config.resolve_role()
    if role_routes.any_enabled():
        router.include_router(
            create_role_router(admin=admin, routes=role_routes),
            tags=["Admin Roles"],
        )

    return router
