from fastapi import APIRouter, Depends, Query, Request
from starlette.status import HTTP_400_BAD_REQUEST

from gt.admin.schemas import (
    AdminListResponseSchema,
    AdminLoginRequestSchema,
    AdminResponseSchema,
)
from gt.admin.settings import AdminSettings
from gt.admin.uow import AdminUOW
from gt.exceptions import ServerException
from gt.ip import IPService
from gt.response import cr
from gt.response._response import get_cookie_response


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
    settings = getattr(admin, "settings", None) or AdminSettings()

    current_admin_dependency = getattr(admin, "current_admin", None)
    if current_admin_dependency is None:
        build_dependency = getattr(admin, "build_current_admin_dependency", None)
        current_admin_dependency = (
            build_dependency() if build_dependency else _admin_auth_not_configured
        )

    router = APIRouter()

    @router.post("/login")
    async def login(request: Request, body: AdminLoginRequestSchema):
        """
        Endpoint to log in an administrator.
        """
        ip_context = IPService.get_ip_context(request)
        async with session_factory() as session:
            login_service = admin.get_services(session).login

            async with AdminUOW(session):
                _, admin_session = await login_service.login(
                    email=body.email.lower(),
                    password=body.password,
                    ip_address=ip_context.ip_address,
                    device=ip_context.device,
                    browser=ip_context.browser,
                    session_expire_minutes=settings.session_expiration_minutes,
                )

            response = cr.success(message="Admin logged in successfully.")

        return get_cookie_response(
            response=response,
            key=settings.session_cookie_name,
            value=str(admin_session.uuid),
            max_age=settings.session_expiration_minutes * 60,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
            path=settings.cookie_path,
        )

    @router.post("/logout")
    async def logout(request: Request):
        """
        Endpoint to log out an administrator.
        """
        session_uuid = request.cookies.get(settings.session_cookie_name)
        if not session_uuid:
            return cr.error(
                error="No active session found.", status_code=HTTP_400_BAD_REQUEST
            )

        async with session_factory() as session:
            login_service = admin.get_services(session).login

            async with AdminUOW(session):
                await login_service.logout(session_uuid=session_uuid)

            response = cr.success(message="Admin logged out successfully.")

        response.delete_cookie(
            key=settings.session_cookie_name,
            domain=settings.cookie_domain,
            path=settings.cookie_path,
        )
        return response

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
