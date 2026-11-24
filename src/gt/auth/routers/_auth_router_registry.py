from gt.auth.routes import AuthRoutesConfig

from ._auth_email_router import create_email_router
from ._auth_oauth_router import create_oauth_router
from ._auth_onboarding_router import create_onboarding_router
from ._auth_password_router import create_password_router
from ._auth_profile_router import create_profile_router
from ._auth_session_router import create_session_router
from ._auth_user_router import create_user_router


def create_auth_router(*, auth, routes: AuthRoutesConfig | None = None):
    """
    Create a router for authentication-related operations.
    """
    from fastapi import APIRouter

    config = routes or AuthRoutesConfig()
    router = APIRouter(prefix="/auth")

    user_routes = config.resolve_user()
    if user_routes.any_enabled():
        router.include_router(
            create_user_router(auth=auth, routes=user_routes),
            tags=["Authentication Core"],
        )

    oauth_routes = config.resolve_oauth()
    if oauth_routes.any_enabled():
        router.include_router(
            create_oauth_router(auth=auth, routes=oauth_routes),
            tags=["Authentication OAuth"],
        )

    onboarding_routes = config.resolve_onboarding()
    if onboarding_routes.any_enabled():
        router.include_router(
            create_onboarding_router(auth=auth, routes=onboarding_routes),
            tags=["Authentication Onboarding"],
        )

    email_routes = config.resolve_email()
    if email_routes.any_enabled():
        router.include_router(
            create_email_router(auth=auth, routes=email_routes),
            tags=["Authentication Email"],
        )

    profile_routes = config.resolve_profile()
    if profile_routes.any_enabled():
        router.include_router(
            create_profile_router(auth=auth, routes=profile_routes),
            tags=["Authentication Profile"],
        )

    password_routes = config.resolve_password()
    if password_routes.any_enabled():
        router.include_router(
            create_password_router(auth=auth, routes=password_routes),
            tags=["Authentication Password"],
        )

    session_routes = config.resolve_session()
    if session_routes.any_enabled():
        router.include_router(
            create_session_router(auth=auth, routes=session_routes),
            tags=["Authentication Session"],
        )

    return router
