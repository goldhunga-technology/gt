from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry

from gt.admin import (
    Admin,
    AdminErrorCode,
    AdminPolicy,
    EndpointRule,
    require_admin_permission,
    require_admin_role,
)
from gt.admin import (
    AuthErrorCode as AdminAuthErrorCode,
)
from gt.admin.dependencies._current_admin import current_admin
from gt.admin.dependencies._require_admin_policy import (
    _build_require_admin_policy_dependency,
)
from gt.auth import Auth, AuthErrorCode
from gt.auth.dependencies._current_session import current_session
from gt.auth.dependencies._current_user import current_user
from gt.exceptions._base_exceptions import InvalidException, UnauthorizedException


def _make_base():
    class Base(DeclarativeBase):
        registry = registry()

    return Base


class TestCentralizedErrorCodes:
    def test_admin_reexports_same_auth_error_code_enum(self):
        assert AdminAuthErrorCode is AuthErrorCode

    async def test_missing_session_cookie_uses_auth_session_invalid_in_auth_and_admin(
        self,
    ):
        base = _make_base()
        session_factory = async_sessionmaker[AsyncSession]()
        auth = Auth(base=base, session_factory=session_factory)
        admin = Admin(base=base, session_factory=session_factory)

        request = MagicMock()
        request.cookies = {}
        request.method = "GET"
        request.url.path = "/admin/me"

        with pytest.raises(InvalidException) as auth_user_exc:
            await auth.current_user()(request, session=MagicMock())
        assert auth_user_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

        with pytest.raises(InvalidException) as auth_session_exc:
            await auth.current_session()(request, session=MagicMock())
        assert auth_session_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

        with pytest.raises(InvalidException) as admin_exc:
            await admin.build_current_admin_dependency()(request, session=MagicMock())
        assert admin_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

        policy = AdminPolicy(
            rules=[EndpointRule("GET", "/admin/me", required_role="superadmin")]
        )
        policy_dep = _build_require_admin_policy_dependency(policy, admin=admin)
        with pytest.raises(InvalidException) as policy_exc:
            await policy_dep(request, session=MagicMock())
        assert policy_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

    async def test_invalid_session_uses_auth_session_invalid_in_auth_and_admin(self):
        services = MagicMock()
        services.session.get_session_by = AsyncMock(return_value=None)
        owner = MagicMock()
        owner.get_services.return_value = services

        with pytest.raises(InvalidException) as user_exc:
            await current_user(auth=owner, session=MagicMock(), session_uuid="bad")
        assert user_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

        with pytest.raises(InvalidException) as sess_exc:
            await current_session(auth=owner, session=MagicMock(), session_uuid="bad")
        assert sess_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

        with pytest.raises(InvalidException) as admin_exc:
            await current_admin(admin=owner, session=MagicMock(), session_uuid="bad")
        assert admin_exc.value.errors == {"code": AuthErrorCode.SESSION_INVALID}

    async def test_admin_guards_use_consistent_auth_and_admin_error_codes(self):
        base = _make_base()
        admin = Admin(base=base, session_factory=async_sessionmaker[AsyncSession]())

        unauth_request = MagicMock()
        unauth_request.cookies = {}

        with pytest.raises(UnauthorizedException) as role_unauth:
            await require_admin_role("superadmin", admin=admin)(
                unauth_request, session=MagicMock()
            )
        assert role_unauth.value.errors == {"code": AuthErrorCode.UNAUTHENTICATED}

        with pytest.raises(UnauthorizedException) as perm_unauth:
            await require_admin_permission("admin.view", admin=admin)(
                unauth_request, session=MagicMock()
            )
        assert perm_unauth.value.errors == {"code": AuthErrorCode.UNAUTHENTICATED}

        # Policy and role guard both report AdminErrorCode.ROLE_REQUIRED when missing a role
        active_admin = MagicMock(id=1)
        active_admin.is_active.return_value = True
        active_session = MagicMock(admin_id=1, is_active=True)

        services = MagicMock()
        services.session.get_session_by = AsyncMock(return_value=active_session)
        services.admin.get_admin_by = AsyncMock(return_value=active_admin)
        services.role.admin_has_role = AsyncMock(return_value=False)
        services.role.admin_has_permission = AsyncMock(return_value=False)

        mock_admin = MagicMock()
        mock_admin.settings = admin.settings
        mock_admin.get_services.return_value = services

        authed_request = MagicMock()
        authed_request.cookies = {admin.settings.session_cookie_name: "sess-1"}
        authed_request.method = "GET"
        authed_request.url.path = "/admin/me"

        with pytest.raises(UnauthorizedException) as role_exc:
            await require_admin_role("superadmin", admin=mock_admin)(
                authed_request, session=MagicMock()
            )
        assert role_exc.value.errors == {"code": AdminErrorCode.ROLE_REQUIRED}

        policy = AdminPolicy(
            rules=[EndpointRule("GET", "/admin/me", required_role="superadmin")]
        )
        with pytest.raises(UnauthorizedException) as policy_role_exc:
            await _build_require_admin_policy_dependency(policy, admin=mock_admin)(
                authed_request, session=MagicMock()
            )
        assert policy_role_exc.value.errors == {"code": AdminErrorCode.ROLE_REQUIRED}

        with pytest.raises(UnauthorizedException) as perm_exc:
            await require_admin_permission("admin.view", admin=mock_admin)(
                authed_request, session=MagicMock()
            )
        assert perm_exc.value.errors == {"code": AdminErrorCode.PERMISSION_DENIED}
