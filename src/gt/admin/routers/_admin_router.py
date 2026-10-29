from fastapi import APIRouter, Depends, Query

from gt.admin.schemas import (
    AdminListResponseSchema,
    AdminResponseSchema,
)
from gt.exceptions import ServerException
from gt.response import cr


def _admin_auth_not_configured():
    """Dependency used when the host has not supplied a current_admin resolver."""
    raise ServerException(
        error="Admin authentication is not configured.",
        errors={"code": "ADMIN_AUTH_NOT_CONFIGURED"},
    )


def create_admin_router(*, admin):
    """
    Create a router for administrator operations.
    """
    session_factory = admin.session_factory
    current_admin_dependency = admin.current_admin or _admin_auth_not_configured

    router = APIRouter()

    @router.get("/users")
    async def list_admin_users(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        search: str | None = Query(default=None, max_length=255),
        status: str | None = Query(default=None, max_length=255),
        _current_admin=Depends(current_admin_dependency),
    ):
        """
        Endpoint to list administrators with pagination and optional filters.
        """
        async with session_factory() as session:
            admin_service = admin.get_services(session).admin
            admins, total = await admin_service.list_admins(
                limit=limit,
                offset=offset,
                search=search,
                status=status,
            )

        return cr.success(
            data=AdminListResponseSchema(
                items=[AdminResponseSchema.model_validate(item) for item in admins],
                total=total,
                limit=limit,
                offset=offset,
            ).model_dump(),
            message="Admins retrieved successfully.",
        )

    return router
