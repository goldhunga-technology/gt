from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gt.auth.models._auth_user_model import AuthUserModel
from gt.auth.repositories._auth_user_repository import AuthUserRepository
from gt.auth.services._auth_email_service import AuthEmailService
from gt.auth.services._auth_login_service import AuthLoginService
from gt.auth.services._auth_user_onboarding_service import (
    AuthUserOnboardingService,
    get_auth_user_onboarding_service,
)
from gt.auth.services._auth_user_service import AuthUserService
from gt.exceptions import ConflictException, DomainException, NotFoundException
from gt.exceptions._base_exceptions import InvalidException

T_USER_MODEL = cast("type[AuthUserModel]", MagicMock())
T_ONBOARDING_MODEL = cast("type[Any]", MagicMock())


class TestTokenGenerator:
    def _service(self) -> AuthUserService:
        return AuthUserService(
            repository=MagicMock(),
            model=T_USER_MODEL,
            account_service=MagicMock(),
            session_service=MagicMock(),
            token_service=MagicMock(),
        )

    def test_random_token_digit_length(self):
        service = self._service()
        for digit in (4, 6, 8):
            token = service._random_token(digit=digit)
            assert len(token) == digit
            assert token.isdigit()
            assert 10 ** (digit - 1) <= int(token) <= (10**digit) - 1

    def test_random_tokens_differ(self):
        service = self._service()
        tokens = {service._random_token() for _ in range(20)}
        assert len(tokens) > 1


def make_login_service(*, user=None, account=None, verify_result=True):
    repository = MagicMock()
    repository.get_by = AsyncMock(return_value=user)
    account_service = MagicMock()
    account_service.get_account_by = AsyncMock(return_value=account)
    session_service = MagicMock()
    session_service.create_session = AsyncMock(return_value="session")
    hash_service = MagicMock()
    hash_service.verify = MagicMock(return_value=verify_result)

    service = AuthLoginService(
        user_repository=repository,
        user_model=T_USER_MODEL,
        account_service=account_service,
        session_service=session_service,
        hash_service=hash_service,
    )
    return service, repository, hash_service


LOGIN_ARGS = {
    "email": "User@Example.com",
    "password": "secret",
    "ip_address": "1.2.3.4",
    "device": "device",
    "browser": "browser",
    "session_expire_minutes": 60,
}


class TestAuthLoginService:
    async def test_login_success(self):
        user = MagicMock()
        account = MagicMock()
        account.hashed_password = "hashed"
        service, repository, _ = make_login_service(
            user=user, account=account, verify_result=True
        )

        result_user, result_session = await service.login(**LOGIN_ARGS)

        assert result_user is user
        assert result_session == "session"
        repository.get_by.assert_awaited_once_with(email="user@example.com")

    async def test_login_invalid_password(self):
        account = MagicMock()
        account.hashed_password = "hashed"
        service, _, _ = make_login_service(
            user=MagicMock(), account=account, verify_result=False
        )

        with pytest.raises(InvalidException):
            await service.login(**LOGIN_ARGS)

    async def test_login_unknown_user(self):
        service, _, hash_service = make_login_service(user=None)

        with pytest.raises(InvalidException):
            await service.login(**LOGIN_ARGS)
        hash_service.dummy_verify.assert_called_once()

    async def test_login_missing_account(self):
        service, _, hash_service = make_login_service(user=MagicMock(), account=None)

        with pytest.raises(InvalidException):
            await service.login(**LOGIN_ARGS)
        hash_service.dummy_verify.assert_called_once()


def make_user(models, *, verified: bool = False):
    user = models["user_model"](
        email="user@example.com", full_name="Test User", avatar_bg="#ffffff"
    )
    if verified:
        user.email_verified_at = datetime.now(UTC)
    return user


def make_token(models, *, expired: bool = False):
    expires_at = (
        datetime.now(UTC) - timedelta(minutes=1)
        if expired
        else datetime.now(UTC) + timedelta(minutes=15)
    )
    return models["token_model"](
        user_id=1,
        type="email_verification",
        token_hash="token-hash",
        expires_at=expires_at,
    )


def make_email_service(*, token, verify_ok=True):
    token_service = MagicMock()
    token_service.get_token_by = AsyncMock(return_value=token)
    token_service.update_token = AsyncMock()
    token_service.delete_tokens_by = AsyncMock()
    user_service = MagicMock()
    user_service.update_user = AsyncMock()
    user_service.get_email_verification_token = AsyncMock(
        return_value=(MagicMock(), "123456")
    )
    hash_service = MagicMock()
    hash_service.verify_deterministic_hash = MagicMock(return_value=verify_ok)

    service = AuthEmailService(
        user_service=user_service,
        token_service=token_service,
        hash_service=hash_service,
    )
    return service, token_service, user_service


class TestAuthEmailService:
    async def test_verify_email_raises_when_already_verified(self, models):
        service, _, _ = make_email_service(token=make_token(models))

        with pytest.raises(ConflictException):
            await service.verify_email(
                user=make_user(models, verified=True), token="123456"
            )

    async def test_verify_email_no_token(self, models):
        service, _, _ = make_email_service(token=None)

        with pytest.raises(NotFoundException):
            await service.verify_email(user=make_user(models), token="123456")

    async def test_verify_email_expired_token(self, models):
        service, _, _ = make_email_service(token=make_token(models, expired=True))

        with pytest.raises(InvalidException):
            await service.verify_email(user=make_user(models), token="123456")

    async def test_verify_email_wrong_token(self, models):
        service, _, _ = make_email_service(token=make_token(models), verify_ok=False)

        with pytest.raises(InvalidException):
            await service.verify_email(user=make_user(models), token="654321")

    async def test_verify_email_success(self, models):
        user = make_user(models)
        token = make_token(models)
        service, token_service, user_service = make_email_service(token=token)

        with patch(
            "gt.auth.services._auth_email_service.event_bus.publish",
            new=AsyncMock(),
        ) as publish:
            result = await service.verify_email(user=user, token="123456")

        assert result is user
        assert user.is_email_verified() is True
        assert token.used_at is not None
        token_service.update_token.assert_awaited_once_with(token)
        user_service.update_user.assert_awaited_once_with(user)
        publish.assert_awaited_once()

    async def test_resend_verification_email(self, models):
        user = make_user(models)
        service, token_service, user_service = make_email_service(
            token=make_token(models)
        )

        with patch(
            "gt.auth.services._auth_email_service.event_bus.publish",
            new=AsyncMock(),
        ) as publish:
            await service.resend_verification_email(
                user=user, email_token_expiry_minutes=15, email_token_digit=6
            )

        token_service.delete_tokens_by.assert_awaited_once_with(
            user_id=user.id, type="email_verification"
        )
        user_service.get_email_verification_token.assert_awaited_once()
        publish.assert_awaited_once()


def make_onboarding_service(*, existing=None, user=None):
    repository = MagicMock()
    repository.get_by = AsyncMock(return_value=existing)
    repository.add = AsyncMock(return_value="onboarding")
    user_service = MagicMock()
    user_service.get_user_by = AsyncMock(return_value=user)
    user_service.update_user = AsyncMock()

    service = AuthUserOnboardingService(
        repository=repository,
        model=T_ONBOARDING_MODEL,
        user_service=user_service,
    )
    return service, repository, user_service


class TestAuthOnboardingService:
    async def test_returns_onboarding_service(self, models):
        from gt.auth.models._auth_user_onboarding_model import (
            create_auth_user_onboarding_model,
        )

        onboarding_model = create_auth_user_onboarding_model(
            models["base"], models["user_model"]
        )
        service = get_auth_user_onboarding_service(
            session=MagicMock(), model=onboarding_model
        )
        assert isinstance(service, AuthUserOnboardingService)

    async def test_add_onboarding_marks_user_onboarded(self):
        user = MagicMock()
        user.is_onboarded = False
        service, _, user_service = make_onboarding_service(existing=None, user=user)

        result = await service.add_onboarding(
            user_id=1, theme="dark", referral_source="friend"
        )

        assert result == "onboarding"
        assert user.is_onboarded is True
        user_service.update_user.assert_awaited_once_with(user)

    async def test_add_onboarding_raises_when_exists(self):
        service, _, _ = make_onboarding_service(existing="row")

        with pytest.raises(InvalidException):
            await service.add_onboarding(user_id=1, theme="dark")


class TestAuthUserServiceBatchLookup:
    def make_service(self):
        service = AuthUserService(
            repository=MagicMock(spec=AuthUserRepository),
            model=T_USER_MODEL,
            account_service=MagicMock(),
            session_service=MagicMock(),
            token_service=MagicMock(),
        )
        return service, service._repository

    async def test_get_users_by_ids_calls_repository(self):
        service, repository = self.make_service()
        user = MagicMock()
        repository.get_by_ids = AsyncMock(return_value=[user])

        result = await service.get_users_by_ids([1, 2])

        repository.get_by_ids.assert_awaited_once_with([1, 2])
        assert result == [user]

    async def test_get_users_by_ids_converts_domain_exception(self):
        service, repository = self.make_service()
        repository.get_by_ids = AsyncMock(
            side_effect=DomainException(error="boom", errors={"code": "ERR"})
        )

        with pytest.raises(DomainException) as exc:
            await service.get_users_by_ids([1])

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ERR"

    async def test_get_users_by_ids_wraps_other_exceptions(self):
        service, repository = self.make_service()
        repository.get_by_ids = AsyncMock(side_effect=RuntimeError("oops"))

        with pytest.raises(DomainException) as exc:
            await service.get_users_by_ids([1])

        assert "Failed to retrieve users." in exc.value.error
