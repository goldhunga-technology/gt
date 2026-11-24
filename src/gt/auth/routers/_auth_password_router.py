from starlette.status import HTTP_200_OK

from gt.auth.routes import AuthPasswordRoutesConfig
from gt.auth.schemas._auth_password_schemas import (
    AuthPasswordResetRequestSchema,
    AuthPasswordResetSchema,
)
from gt.response import cr

from ..uow import AuthUOW


def create_password_router(*, auth, routes: AuthPasswordRoutesConfig | None = None):
    """
    Create a router for password operations.
    """
    session_factory = auth.session_factory
    route_config = routes or AuthPasswordRoutesConfig()

    password_reset_token_digit = auth.settings.password_reset_token_digit
    password_reset_token_expiry_minutes = (
        auth.settings.password_reset_token_expiry_minutes
    )

    from fastapi import APIRouter

    router = APIRouter()

    if route_config.is_enabled("forgot_password"):

        @router.post("/forgot-password")
        async def forgot_password(body: AuthPasswordResetRequestSchema):
            """
            Endpoint to request a password reset token for a user.
            """
            async with session_factory() as session:
                password_service = auth.get_services(session).password

                async with AuthUOW(session):
                    await password_service.request_password_reset(
                        email=body.email,
                        password_reset_token_expiry_minutes=password_reset_token_expiry_minutes,
                        password_reset_token_digit=password_reset_token_digit,
                    )

            return cr.success(
                message="If the email exists, a password reset token has been sent.",
                status_code=HTTP_200_OK,
            )

    if route_config.is_enabled("reset_password"):

        @router.post("/reset-password")
        async def reset_password(body: AuthPasswordResetSchema):
            """
            Endpoint to reset a user's password using a password reset token.
            """
            async with session_factory() as session:
                password_service = auth.get_services(session).password

                async with AuthUOW(session):
                    await password_service.reset_password(
                        token=body.token,
                        new_password=body.new_password,
                    )

            return cr.success(
                message="Password reset successfully.",
                status_code=HTTP_200_OK,
            )

    return router
