from fastapi.requests import Request
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from gt.auth.routes import AuthUserRoutesConfig
from gt.auth.schemas._auth_schemas import AuthLoginRequestSchema
from gt.ip import IPService
from gt.response import cr
from gt.response._response import get_cookie_response

from ..uow import AuthUOW


def create_user_router(*, auth, routes: AuthUserRoutesConfig | None = None):
    """
    Create a router for user-related operations.
    """
    session_factory = auth.session_factory
    settings = auth.settings
    user_model = auth.user_model
    user_register_schema = auth.user_register_schema
    route_config = routes or AuthUserRoutesConfig()

    from fastapi import APIRouter

    router = APIRouter()

    if route_config.is_enabled("register"):

        @router.post("/register")
        async def register_user(request: Request, body: user_register_schema):  # type: ignore
            """
            Endpoint to register a new user.
            """
            ip_context = IPService.get_ip_context(request)
            async with session_factory() as session:
                user_service = auth.get_services(session).user

                async with AuthUOW(session):
                    user = user_model(
                        **body.model_dump(exclude={"password", "email"}),
                        email=body.email.lower(),
                    )
                    _, user_session = await user_service.create_user(
                        user,
                        password=body.password,
                        ip_address=ip_context.ip_address,
                        device=ip_context.device,
                        browser=ip_context.browser,
                        session_expire_minutes=settings.session_expiration_minutes,
                        email_token_expiry_minutes=settings.email_verification_token_expiry_minutes,
                        email_token_digit=settings.email_verification_token_digit,
                    )

            response = cr.success(
                message="User registered successfully.", status_code=HTTP_201_CREATED
            )
            return get_cookie_response(
                response=response,
                key="session_uuid",
                value=str(user_session.uuid),
                max_age=settings.session_expiration_minutes * 60,
                httponly=settings.cookie_httponly,
                secure=settings.cookie_secure,
                samesite=settings.cookie_samesite,
                domain=settings.cookie_domain,
                path=settings.cookie_path,
            )

    if route_config.is_enabled("login"):

        @router.post("/login")
        async def login(request: Request, body: AuthLoginRequestSchema):
            """
            Endpoint to log in a user.
            """
            ip_context = IPService.get_ip_context(request)
            async with session_factory() as session:
                login_service = auth.get_services(session).login

                async with AuthUOW(session):
                    _, user_session = await login_service.login(
                        email=body.email.lower(),
                        password=body.password,
                        ip_address=ip_context.ip_address,
                        device=ip_context.device,
                        browser=ip_context.browser,
                        session_expire_minutes=settings.session_expiration_minutes,
                    )

                response = cr.success(
                    message="User logged in successfully.",
                )

            return get_cookie_response(
                response=response,
                key="session_uuid",
                value=str(user_session.uuid),
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
            Endpoint to log out a user.
            """
            session_uuid = request.cookies.get("session_uuid")
            if not session_uuid:
                return cr.error(
                    error="No active session found.", status_code=HTTP_400_BAD_REQUEST
                )

            async with session_factory() as session:
                login_service = auth.get_services(session).login

                async with AuthUOW(session):
                    await login_service.logout(session_uuid=session_uuid)

                response = cr.success(message="User logged out successfully.")

            # Clear the session cookie
            response.delete_cookie(
                key="session_uuid",
                domain=settings.cookie_domain,
                path=settings.cookie_path,
            )
            return response

    return router
