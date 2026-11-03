from ._admin_router import create_admin_router
from ._role_router import create_role_router


def create_admins_router(*, admin):
    """
    Create a router for admin-related operations.
    """

    from fastapi import APIRouter

    router = APIRouter(prefix="/admin")
    router.include_router(create_admin_router(admin=admin), tags=["Admin"])
    router.include_router(create_role_router(admin=admin), tags=["Admin Roles"])

    return router
