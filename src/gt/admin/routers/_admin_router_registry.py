from ._admin_router import create_admin_router


def create_admins_router(*, admin):
    """
    Create a router for admin-related operations.
    """

    from fastapi import APIRouter

    router = APIRouter(prefix="/admin")
    router.include_router(create_admin_router(admin=admin), tags=["Admin"])

    return router
