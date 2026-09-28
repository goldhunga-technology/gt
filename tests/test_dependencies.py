from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gt.auth.dependencies._current_user import current_user
from gt.auth.dependencies._guards._require_access_guard import require_access
from gt.exceptions import DomainException
from gt.exceptions._base_exceptions import InvalidException, UnauthorizedException


def make_services(*, user_session=None, user=None):
    services = MagicMock()
    services.session.get_session_by = AsyncMock(return_value=user_session)
    services.user.get_user_by = AsyncMock(return_value=user)
    return services


def make_auth(*, user_session=None, user=None):
    auth = MagicMock()
    auth.get_services.return_value = make_services(user_session=user_session, user=user)
    return auth


class TestCurrentUser:
    async def test_returns_user_for_valid_session(self):
        user = MagicMock()
        user.is_active.return_value = True
        user_session = MagicMock()
        user_session.is_active = True
        auth = make_auth(user_session=user_session, user=user)

        result = await current_user(
            auth=auth, session=MagicMock(), session_uuid="valid-uuid"
        )

        assert result is user
        auth.get_services.assert_called_once()

    async def test_returns_user_with_language(self, models):
        user = models["user_model"](
            email="user@example.com",
            full_name="Test User",
            avatar_bg="#ffffff",
            language="ne",
        )
        user_session = MagicMock()
        user_session.is_active = True
        auth = make_auth(user_session=user_session, user=user)

        result = await current_user(
            auth=auth, session=MagicMock(), session_uuid="valid-uuid"
        )

        assert result is user
        assert result.language == "ne"

    async def test_raises_for_invalid_session(self):
        auth = make_auth(user_session=None)

        with pytest.raises(InvalidException):
            await current_user(auth=auth, session=MagicMock(), session_uuid="bad-uuid")

    async def test_raises_for_inactive_user(self):
        user = MagicMock()
        user.is_active.return_value = False
        user_session = MagicMock()
        user_session.is_active = True
        auth = make_auth(user_session=user_session, user=user)

        with pytest.raises(InvalidException):
            await current_user(
                auth=auth, session=MagicMock(), session_uuid="valid-uuid"
            )


class TestRequireAccess:
    async def test_unauthenticated_raises(self, auth):
        dependency = require_access(auth=auth)
        request = MagicMock()
        request.cookies = {}

        with pytest.raises(UnauthorizedException):
            await dependency(request, session=MagicMock())

    async def test_returns_none_when_not_required_and_no_session(self, auth):
        dependency = require_access(auth=auth, authenticated=False)
        request = MagicMock()
        request.cookies = {}

        result = await dependency(request, session=MagicMock())

        assert result is None

    async def test_returns_user_when_authenticated(self, auth):
        user = MagicMock()
        request = MagicMock()
        request.cookies = {"session_uuid": "valid-uuid"}

        with patch(
            "gt.auth.dependencies._current_user.current_user",
            new=AsyncMock(return_value=user),
        ):
            dependency = require_access(auth=auth)
            result = await dependency(request, session=MagicMock())

        assert result is user

    async def test_email_verified_policy_is_enforced(self, auth):
        user = MagicMock()
        user.is_email_verified.return_value = False
        request = MagicMock()
        request.cookies = {"session_uuid": "valid-uuid"}

        with patch(
            "gt.auth.dependencies._current_user.current_user",
            new=AsyncMock(return_value=user),
        ):
            dependency = require_access(auth=auth, email_verified=True)
            with pytest.raises(DomainException):
                await dependency(request, session=MagicMock())


class TestBelongsToOrgPolicy:
    def _dependency(self, *, auth):
        request = MagicMock()
        request.cookies = {"session_uuid": "valid-uuid"}
        with patch(
            "gt.auth.dependencies._current_user.current_user",
            new=AsyncMock(return_value=MagicMock()),
        ):
            return require_access(auth=auth, belongs_to_org=True)

    async def test_raises_when_resolver_not_configured(self, auth):
        dependency = self._dependency(auth=auth)

        with pytest.raises(DomainException) as exc:
            await dependency(MagicMock(), session=MagicMock())

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ORGANIZATION_NOT_SET_UP"

    async def test_passes_when_resolver_passes(self, auth):
        resolver = AsyncMock()
        auth.configure_belongs_to_org_check(resolver)
        user = MagicMock()
        session = MagicMock()
        request = MagicMock()
        request.cookies = {"session_uuid": "valid-uuid"}

        with patch(
            "gt.auth.dependencies._current_user.current_user",
            new=AsyncMock(return_value=user),
        ):
            dependency = require_access(auth=auth, belongs_to_org=True)
            result = await dependency(request, session=session)

        assert result is user
        resolver.check_user_belongs_to_organization.assert_awaited_once_with(
            user=user, session=session
        )

    async def test_propagates_resolver_denial(self, auth):
        async def deny(*, user, session):
            raise DomainException(
                error="Organization is required.",
                errors={"code": "ORGANIZATION_REQUIRED"},
            )

        check = MagicMock()
        check.check_user_belongs_to_organization = deny
        auth.configure_belongs_to_org_check(check)
        dependency = self._dependency(auth=auth)

        with pytest.raises(DomainException) as exc:
            await dependency(MagicMock(), session=MagicMock())

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ORGANIZATION_REQUIRED"

    def test_policy_can_reference_belongs_to_org(self, auth):
        auth.configure_belongs_to_org_check(AsyncMock())
        auth.register_policy(name="member", checks=["email_verified", "belongs_to_org"])

        @auth.policy("member")
        async def handler():
            return "ok"

        assert handler is not None

    def test_policy_rejects_unknown_check(self, auth):
        auth.register_policy(name="member", checks=["nonsense"])

        with pytest.raises(ValueError):

            @auth.policy("member")
            async def handler():
                return "ok"
