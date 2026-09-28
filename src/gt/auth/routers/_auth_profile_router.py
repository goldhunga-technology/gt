from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK

from gt.auth.dependencies._guards._require_access_guard import require_access
from gt.auth.schemas._auth_profile_schemas import (
    AuthChangeLanguageSchema,
    AuthDeactivateSchema,
    AuthProfileUpdateSchema,
)
from gt.response import cr

from ..uow import AuthUOW


def create_profile_router(*, auth):
    """
    Create a router for user profile operations.
    """
    router = APIRouter()

    @router.patch("/profile")
    async def update_profile(
        body: AuthProfileUpdateSchema,
        session: AsyncSession = Depends(auth.get_db_session),
        current_user=Depends(require_access(auth=auth, authenticated=True)),
    ):
        """
        Endpoint to update the current user's profile.
        """
        user_service = auth.get_services(session).user

        async with AuthUOW(session):
            updated_user = await user_service.update_profile(
                user=current_user,
                **body.model_dump(exclude_unset=True),
            )

        return cr.success(
            data={
                "uuid": updated_user.uuid,
                "full_name": updated_user.full_name,
                "email": updated_user.email,
                "avatar": updated_user.avatar,
                "avatar_bg": updated_user.avatar_bg,
                "language": updated_user.language,
            },
            message="Profile updated successfully.",
            status_code=HTTP_200_OK,
        )

    @router.patch("/language")
    async def change_language(
        body: AuthChangeLanguageSchema,
        session: AsyncSession = Depends(auth.get_db_session),
        current_user=Depends(require_access(auth=auth, authenticated=True)),
    ):
        """
        Endpoint to change the current user's language.
        """
        user_service = auth.get_services(session).user

        async with AuthUOW(session):
            updated_user = await user_service.update_language(
                user=current_user,
                language=body.language,
            )

        return cr.success(
            data={
                "language": updated_user.language,
            },
            message="Language updated successfully.",
            status_code=HTTP_200_OK,
        )

    @router.post("/deactivate")
    async def deactivate_user(
        body: AuthDeactivateSchema,
        session: AsyncSession = Depends(auth.get_db_session),
        current_user=Depends(require_access(auth=auth, authenticated=True)),
    ):
        """
        Endpoint to deactivate the current user's account.
        """
        user_service = auth.get_services(session).user

        async with AuthUOW(session):
            await user_service.deactivate_user(
                user=current_user,
                password=body.password,
            )

        return cr.success(
            message="User deactivated successfully.",
            status_code=HTTP_200_OK,
        )

    return router
