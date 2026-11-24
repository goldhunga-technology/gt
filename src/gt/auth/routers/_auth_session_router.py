from typing import Literal

from fastapi import Query
from fastapi.requests import Request

from gt.auth.routes import AuthSessionRoutesConfig
from gt.auth.schemas._auth_session_schema import CurrentSessionResponseSchema
from gt.response import cr


def create_session_router(*, auth, routes: AuthSessionRoutesConfig | None = None):
    """
    Create a router for session-related operations.
    """
    session_factory = auth.session_factory
    route_config = routes or AuthSessionRoutesConfig()

    from fastapi import APIRouter

    router = APIRouter(prefix="/session")

    if route_config.is_enabled("current"):

        @router.get("/current")
        async def current_session(request: Request):
            """
            Endpoint to log out a user by invalidating their session.
            """
            session_uuid = request.cookies.get("session_uuid")
            if not session_uuid:
                return cr.error(
                    error="No session found.",
                    errors={"code": "SESSION_NOT_FOUND"},
                )

            async with session_factory() as session:
                user_session_service = auth.get_services(session).session

                # Invalidate the user's session here (implementation depends on your session management)
                current = await user_session_service.get_session_by(uuid=session_uuid)

                if not current or not current.is_active:
                    return cr.error(
                        error="Invalid or expired session.",
                        errors={"code": "SESSION_INVALID"},
                    )

            return cr.success(
                data=CurrentSessionResponseSchema.model_validate(
                    current,
                ).model_dump(),
                message="Successfully retrieved current session.",
            )

    if route_config.is_enabled("all"):

        @router.get("/all")
        async def all_sessions(
            request: Request,
            status: Literal["active", "inactive", "all"] = Query(
                "all",
                description="Filter sessions by status: 'active', 'inactive', or 'all'",
            ),
        ):
            """
            Endpoint to retrieve all sessions for the current user.
            """
            session_uuid = request.cookies.get("session_uuid")
            if not session_uuid:
                return cr.error(
                    error="No session found.",
                    errors={"code": "SESSION_NOT_FOUND"},
                )

            async with session_factory() as session:
                user_session_service = auth.get_services(session).session

                # Retrieve all sessions for the current user (implementation depends on your session management)
                current = await user_session_service.get_session_by(uuid=session_uuid)

                if not current or not current.is_active:
                    return cr.error(
                        error="Invalid or expired session.",
                        errors={"code": "SESSION_INVALID"},
                    )

                all_sessions = await user_session_service.list_sessions_by_user(
                    user_id=current.user_id
                )
                if status != "all":
                    is_active = status == "active"
                    all_sessions = [s for s in all_sessions if s.is_active == is_active]

            return cr.success(
                data=[
                    CurrentSessionResponseSchema.model_validate(s).model_dump()
                    for s in all_sessions
                ],
                message="Successfully retrieved all sessions.",
            )

    return router
