from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gt.auth.models._auth_user_model import AuthUserModel
from gt.auth.services._auth_user_service import AuthUserService
from gt.exceptions import ConflictException
from gt.exceptions._base_exceptions import InvalidException

T_USER_MODEL = cast("type[AuthUserModel]", MagicMock())


def make_user(models, *, status: str = "active"):
    user = models["user_model"](
        email="user@example.com", full_name="Test User", avatar_bg="#ffffff"
    )
    user.status = status
    return user


def make_user_service(*, user, account=None, password_verify=True):
    repository = MagicMock()
    repository.update = AsyncMock(return_value=user)
    account_service = MagicMock()
    account_service.get_account_by = AsyncMock(return_value=account)
    account_service._hash_service = MagicMock()
    account_service._hash_service.verify = MagicMock(return_value=password_verify)
    session_service = MagicMock()
    session_service.invalidate_user_sessions = AsyncMock()
    token_service = MagicMock()

    service = AuthUserService(
        repository=repository,
        model=T_USER_MODEL,
        account_service=account_service,
        session_service=session_service,
        token_service=token_service,
    )
    return service, repository, account_service, session_service


class TestUpdateProfile:
    async def test_update_profile_success(self, models):
        user = make_user(models)
        service, repository, _, _ = make_user_service(user=user)

        with patch(
            "gt.auth.services._auth_user_service.event_bus.publish",
            new=AsyncMock(),
        ) as publish:
            updated = await service.update_profile(
                user=user, full_name="New Name", avatar="a.png"
            )

        assert updated.full_name == "New Name"
        assert updated.avatar == "a.png"
        repository.update.assert_awaited_once_with(user)
        publish.assert_awaited_once()

    async def test_update_profile_ignores_none_fields(self, models):
        user = make_user(models)
        service, _, _, _ = make_user_service(user=user)

        with patch(
            "gt.auth.services._auth_user_service.event_bus.publish",
            new=AsyncMock(),
        ):
            updated = await service.update_profile(
                user=user, full_name=None, avatar=None
            )

        assert updated.full_name == "Test User"
        assert updated.avatar_bg == "#ffffff"

    async def test_update_profile_with_language(self, models):
        user = make_user(models)
        service, repository, _, _ = make_user_service(user=user)

        with patch(
            "gt.auth.services._auth_user_service.event_bus.publish",
            new=AsyncMock(),
        ) as publish:
            updated = await service.update_profile(user=user, language="es")

        assert updated.language == "es"
        repository.update.assert_awaited_once_with(user)
        publish.assert_awaited_once()


class TestUpdateLanguage:
    async def test_update_language_success(self, models):
        user = make_user(models)
        service, repository, _, _ = make_user_service(user=user)

        with patch(
            "gt.auth.services._auth_user_service.event_bus.publish",
            new=AsyncMock(),
        ) as publish:
            updated = await service.update_language(user=user, language="ne")

        assert updated.language == "ne"
        repository.update.assert_awaited_once_with(user)
        publish.assert_awaited_once()


class TestDeactivateUser:
    async def test_deactivate_already_inactive(self, models):
        user = make_user(models, status="inactive")
        service, _, _, _ = make_user_service(user=user)

        with pytest.raises(ConflictException):
            await service.deactivate_user(user=user, password="secret")

    async def test_deactivate_wrong_password(self, models):
        user = make_user(models)
        account = MagicMock()
        account.hashed_password = "hashed"
        service, _, _, _ = make_user_service(
            user=user, account=account, password_verify=False
        )

        with pytest.raises(InvalidException):
            await service.deactivate_user(user=user, password="wrong")

    async def test_deactivate_success(self, models):
        user = make_user(models)
        account = MagicMock()
        account.hashed_password = "hashed"
        service, _, _, session_service = make_user_service(user=user, account=account)

        with patch(
            "gt.auth.services._auth_user_service.event_bus.publish",
            new=AsyncMock(),
        ) as publish:
            updated = await service.deactivate_user(user=user, password="secret")

        assert updated.is_active() is False
        assert updated.status == "inactive"
        session_service.invalidate_user_sessions.assert_awaited_once_with(
            user_id=user.id
        )
        publish.assert_awaited_once()

    async def test_deactivate_without_password(self, models):
        user = make_user(models)
        service, _, _, session_service = make_user_service(user=user)

        with patch(
            "gt.auth.services._auth_user_service.event_bus.publish",
            new=AsyncMock(),
        ):
            updated = await service.deactivate_user(user=user)

        assert updated.status == "inactive"
        session_service.invalidate_user_sessions.assert_awaited_once_with(
            user_id=user.id
        )
