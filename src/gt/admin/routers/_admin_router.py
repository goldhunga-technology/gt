from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from starlette.status import HTTP_400_BAD_REQUEST

from gt.admin.errors import AdminErrorCode
from gt.admin.routes import AdminCoreRoutesConfig
from gt.admin.schemas import (
    AdminListResponseSchema,
    AdminLoginRequestSchema,
    AdminMeResponseSchema,
    AdminResponseSchema,
)
from gt.admin.settings import AdminSettings
from gt.admin.uow import AdminUOW
from gt.auth.errors import AuthErrorCode
from gt.exceptions import ServerException
from gt.ip import IPService
from gt.response import cr
from gt.response._response import get_cookie_response


def _admin_auth_not_configured():
    """Dependency used when the host has not supplied a current_admin resolver."""
    raise ServerException(
        error="Admin authentication is not configured.",
        errors={"code": AdminErrorCode.ADMIN_AUTH_NOT_CONFIGURED},
    )


def create_admin_router(*, admin, routes: AdminCoreRoutesConfig | None = None):
    """
    Create a router for administrator operations.
    """
    session_factory = admin.session_factory
    settings = getattr(admin, "settings", None) or AdminSettings()
    route_config = routes or AdminCoreRoutesConfig()

    current_admin_dependency = getattr(admin, "current_admin", None)
    if current_admin_dependency is None:
        build_dependency = getattr(admin, "build_current_admin_dependency", None)
        current_admin_dependency = (
            build_dependency() if build_dependency else _admin_auth_not_configured
        )

    router = APIRouter()

    if route_config.is_enabled("login"):

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

    if route_config.is_enabled("logout"):

        @router.post("/logout")
        async def logout(request: Request):
            """
            Endpoint to log out an administrator.
            """
            session_uuid = request.cookies.get(settings.session_cookie_name)
            if not session_uuid:
                return cr.error(
                    error="No active session found.",
                    errors={"code": AuthErrorCode.SESSION_INVALID},
                    status_code=HTTP_400_BAD_REQUEST,
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

    if route_config.is_enabled("me"):

        @router.get("/me")
        async def get_current_admin_profile(
            _current_admin: Annotated[Any, Depends(current_admin_dependency)],
        ):
            """
            Endpoint to retrieve the currently authenticated administrator's profile,
            assigned roles, and effective permissions.
            """
            roles_slugs: list[str] = []
            permissions: list[str] = []
            async with session_factory() as session:
                services = admin.get_services(session)
                role_service = getattr(services, "role", None)
                if role_service is not None:
                    _, roles = await role_service.get_admin_roles(_current_admin.uuid)
                    roles_slugs = [role.slug for role in roles if role.is_active()]
                    permissions = await role_service.get_permissions_for_admin(
                        _current_admin.id
                    )

            base_data = AdminResponseSchema.model_validate(_current_admin).model_dump()
            payload = AdminMeResponseSchema(
                **base_data,
                roles=roles_slugs,
                permissions=permissions,
            ).model_dump()

            return cr.success(
                data=payload,
                message="Admin profile retrieved successfully.",
            )

    if route_config.is_enabled("list_users"):

        @router.get("/users")
        async def list_admin_users(
            _current_admin: Annotated[Any, Depends(current_admin_dependency)],
            limit: Annotated[int, Query(ge=1, le=100)] = 20,
            offset: Annotated[int, Query(ge=0)] = 0,
            search: Annotated[str | None, Query(max_length=255)] = None,
            status: Annotated[str | None, Query(max_length=255)] = None,
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
