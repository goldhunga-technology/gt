from datetime import UTC, datetime, timedelta

import pytest

from gt.auth.policies._user_policies import UserPolicies
from gt.exceptions import DomainException


def make_user(
    models,
    *,
    email_verified: bool = False,
    onboarded: bool = False,
    status: str = "active",
):
    user = models["user_model"](
        email="user@example.com",
        full_name="Test User",
        avatar_bg="#ffffff",
        is_onboarded=onboarded,
        status=status,
    )
    if email_verified:
        user.email_verified_at = datetime.now(UTC)
    return user


def make_session(models, *, hours_from_now: int = 1):
    return models["session_model"](
        user_id=1,
        expires_at=datetime.now(UTC) + timedelta(hours=hours_from_now),
    )


class TestAuthUserModel:
    def test_is_active(self, models):
        assert make_user(models, status="active").is_active() is True
        assert make_user(models, status="inactive").is_active() is False

    def test_is_email_verified(self, models):
        assert make_user(models, email_verified=False).is_email_verified() is False
        assert make_user(models, email_verified=True).is_email_verified() is True

    def test_language_defaults_to_en(self, models):
        user = make_user(models)
        assert user.language == "en"

    def test_language_custom(self, models):
        user = models["user_model"](
            email="user@example.com",
            full_name="Test User",
            avatar_bg="#ffffff",
            language="fr",
        )
        assert user.language == "fr"


class TestAuthUserSessionModel:
    def test_active_session(self, models):
        session = make_session(models)
        assert session.is_expired is False
        assert session.is_active is True

    def test_expired_session(self, models):
        session = make_session(models, hours_from_now=-1)
        assert session.is_expired is True
        assert session.is_active is False

    def test_revoked_session(self, models):
        session = make_session(models)
        session.revoke()
        assert session.revoked_at is not None
        assert session.is_active is False


class TestUserPolicies:
    def test_require_email_verified_raises_when_unverified(self, models):
        with pytest.raises(DomainException) as exc:
            UserPolicies.require_email_verified(make_user(models, email_verified=False))
        assert exc.value.errors == {"code": "EMAIL_UNVERIFIED"}

    def test_require_email_verified_passes(self, models):
        UserPolicies.require_email_verified(make_user(models, email_verified=True))

    def test_require_onboarding_raises_when_not_onboarded(self, models):
        with pytest.raises(DomainException) as exc:
            UserPolicies.require_onboarding(make_user(models, onboarded=False))
        assert exc.value.errors == {"code": "ONBOARDING_REQUIRED"}

    def test_require_onboarding_passes(self, models):
        UserPolicies.require_onboarding(make_user(models, onboarded=True))
