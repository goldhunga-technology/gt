import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry
from starlette.middleware.sessions import SessionMiddleware

from gt.admin import (
    Admin,
    AdminCoreRoutesConfig,
    AdminPolicy,
    AdminRoleRoutesConfig,
    AdminRoutesConfig,
    EndpointRule,
)
from gt.auth import (
    Auth,
    AuthEmailRoutesConfig,
    AuthOAuthRoutesConfig,
    AuthOnboardingRoutesConfig,
    AuthPasswordRoutesConfig,
    AuthProfileRoutesConfig,
    AuthRoutesConfig,
    AuthSessionRoutesConfig,
    AuthUserRoutesConfig,
)
from gt.exceptions import DomainException
from gt.organizations import (
    AdminOrganizationRoutesConfig,
    OrganizationMemberRoutesConfig,
    OrganizationRoutesConfig,
    Organizations,
    OrganizationsRoutesConfig,
)


def _make_base():
    class Base(DeclarativeBase):
        registry = registry()

    return Base


def _route_endpoints(app: FastAPI) -> set[tuple[str, str]]:
    """Return all ``(METHOD, PATH)`` pairs registered on *app*'s OpenAPI schema."""
    result: set[tuple[str, str]] = set()
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            result.add((method.upper(), path))
    return result


async def _asgi_status(app: FastAPI, method: str, path: str) -> int:
    """Send a minimal ASGI HTTP request to *app* and return the HTTP status code."""
    status = 0

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    return status


def _make_auth() -> Auth:
    base = _make_base()
    return Auth(base=base, session_factory=async_sessionmaker[AsyncSession]())


def _make_organizations(*, with_admin: bool = False) -> Organizations:
    base = _make_base()
    session_factory = async_sessionmaker[AsyncSession]()
    auth = Auth(base=base, session_factory=session_factory)
    admin = Admin(base=base, session_factory=session_factory) if with_admin else None
    return Organizations(
        base=base,
        session_factory=session_factory,
        user_model=auth.user_model,
        admin=admin,
    )


def _make_admin(*, policy: AdminPolicy | None = None) -> Admin:
    base = _make_base()
    return Admin(
        base=base,
        session_factory=async_sessionmaker[AsyncSession](),
        admin_policy=policy,
    )


ALL_AUTH_ENDPOINTS: set[tuple[str, str]] = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/logout"),
    ("GET", "/auth/oauth/login/{provider}"),
    ("GET", "/auth/oauth/callback/{provider}"),
    ("POST", "/auth/onboarding"),
    ("POST", "/auth/email-verification"),
    ("POST", "/auth/resend-email-verification"),
    ("PATCH", "/auth/profile"),
    ("PATCH", "/auth/language"),
    ("POST", "/auth/deactivate"),
    ("POST", "/auth/forgot-password"),
    ("POST", "/auth/reset-password"),
    ("GET", "/auth/session/current"),
    ("GET", "/auth/session/all"),
}

ALL_ORG_ENDPOINTS: set[tuple[str, str]] = {
    ("POST", "/organizations/"),
    ("GET", "/organizations/"),
    ("GET", "/organizations/{slug}"),
    ("PATCH", "/organizations/{slug}"),
    ("POST", "/organizations/{organization_slug}/members"),
    ("GET", "/organizations/{organization_slug}/members"),
    ("PATCH", "/organizations/{organization_slug}/members/{member_uuid}"),
    ("DELETE", "/organizations/{organization_slug}/members/{member_uuid}"),
}

ALL_ADMIN_ORG_ENDPOINTS: set[tuple[str, str]] = {
    ("GET", "/admin/organizations"),
    ("PATCH", "/admin/organizations/{organization_uuid}/status"),
}

ALL_ADMIN_ENDPOINTS: set[tuple[str, str]] = {
    ("POST", "/admin/login"),
    ("POST", "/admin/logout"),
    ("GET", "/admin/me"),
    ("GET", "/admin/users"),
    ("GET", "/admin/permissions"),
    ("POST", "/admin/roles"),
    ("GET", "/admin/roles"),
    ("GET", "/admin/roles/{role_uuid}"),
    ("PATCH", "/admin/roles/{role_uuid}"),
    ("DELETE", "/admin/roles/{role_uuid}"),
    ("GET", "/admin/admins/{admin_uuid}/roles"),
    ("POST", "/admin/admins/{admin_uuid}/roles"),
    ("DELETE", "/admin/admins/{admin_uuid}/roles/{role_uuid}"),
}


class TestAuthRoutesConfig:
    @pytest.mark.parametrize("routes", [None, True, AuthRoutesConfig()])
    def test_defaults_register_all_auth_routes(self, routes):
        app = FastAPI()
        _make_auth().init_app(app, routes=routes)
        assert _route_endpoints(app) == ALL_AUTH_ENDPOINTS

    @pytest.mark.parametrize("routes", [False, AuthRoutesConfig.disabled()])
    def test_disable_all_auth_routes_keeps_exceptions_and_middleware(self, routes):
        app = FastAPI()
        _make_auth().init_app(app, routes=routes)

        assert _route_endpoints(app) == set()
        assert DomainException in app.exception_handlers
        assert any(m.cls is SessionMiddleware for m in app.user_middleware)

    def test_disable_router_groups(self):
        app = FastAPI()
        _make_auth().init_app(
            app,
            routes=AuthRoutesConfig(
                oauth=False,
                onboarding=False,
                password=False,
            ),
        )

        endpoints = _route_endpoints(app)
        expected = ALL_AUTH_ENDPOINTS - {
            ("GET", "/auth/oauth/login/{provider}"),
            ("GET", "/auth/oauth/callback/{provider}"),
            ("POST", "/auth/onboarding"),
            ("POST", "/auth/forgot-password"),
            ("POST", "/auth/reset-password"),
        }
        assert endpoints == expected

    def test_disable_individual_endpoints(self):
        app = FastAPI()
        _make_auth().init_app(
            app,
            routes=AuthRoutesConfig(
                user=AuthUserRoutesConfig(register=False),
                oauth=AuthOAuthRoutesConfig(callback=False),
                email=AuthEmailRoutesConfig(resend=False),
                profile=AuthProfileRoutesConfig(deactivate=False),
                password=AuthPasswordRoutesConfig(forgot_password=False),
                session=AuthSessionRoutesConfig(all=False),
                onboarding=AuthOnboardingRoutesConfig(register=False),
            ),
        )

        endpoints = _route_endpoints(app)
        expected = ALL_AUTH_ENDPOINTS - {
            ("POST", "/auth/register"),
            ("GET", "/auth/oauth/callback/{provider}"),
            ("POST", "/auth/resend-email-verification"),
            ("POST", "/auth/deactivate"),
            ("POST", "/auth/forgot-password"),
            ("GET", "/auth/session/all"),
            ("POST", "/auth/onboarding"),
        }
        assert endpoints == expected

    def test_allow_list_mode(self):
        app = FastAPI()
        _make_auth().init_app(
            app,
            routes=AuthRoutesConfig(
                default=False,
                user=AuthUserRoutesConfig(default=False, login=True, logout=True),
                session=True,
            ),
        )

        assert _route_endpoints(app) == {
            ("POST", "/auth/login"),
            ("POST", "/auth/logout"),
            ("GET", "/auth/session/current"),
            ("GET", "/auth/session/all"),
        }

    def test_prefix_combined_with_routes_config(self):
        app = FastAPI()
        _make_auth().init_app(
            app,
            prefix="/api/v1",
            routes=AuthRoutesConfig(
                default=False,
                user=AuthUserRoutesConfig(default=False, login=True),
            ),
        )

        assert _route_endpoints(app) == {("POST", "/api/v1/auth/login")}

    def test_invalid_routes_argument_raises_type_error(self):
        app = FastAPI()
        with pytest.raises(TypeError):
            _make_auth().init_app(app, routes="invalid")  # type: ignore[arg-type]

        with pytest.raises(TypeError):
            _make_auth().init_app(
                app,
                routes=AuthRoutesConfig(user="invalid"),  # type: ignore[arg-type]
            )


class TestOrganizationsRoutesConfig:
    @pytest.mark.parametrize("routes", [None, True, OrganizationsRoutesConfig()])
    def test_defaults_without_admin(self, routes):
        app = FastAPI()
        _make_organizations(with_admin=False).init_app(app, routes=routes)
        assert _route_endpoints(app) == ALL_ORG_ENDPOINTS

    def test_defaults_with_admin(self):
        app = FastAPI()
        _make_organizations(with_admin=True).init_app(app)
        assert _route_endpoints(app) == ALL_ORG_ENDPOINTS | ALL_ADMIN_ORG_ENDPOINTS

    @pytest.mark.parametrize("routes", [False, OrganizationsRoutesConfig.disabled()])
    def test_disable_all_organization_routes_including_admin(self, routes):
        app = FastAPI()
        _make_organizations(with_admin=True).init_app(app, routes=routes)
        assert _route_endpoints(app) == set()

    def test_disable_groups_and_individual_endpoints(self):
        app = FastAPI()
        _make_organizations(with_admin=True).init_app(
            app,
            routes=OrganizationsRoutesConfig(
                organization=OrganizationRoutesConfig(create=False, update=False),
                member=OrganizationMemberRoutesConfig(remove=False),
                admin=AdminOrganizationRoutesConfig(update_status=False),
            ),
        )

        expected = (ALL_ORG_ENDPOINTS | ALL_ADMIN_ORG_ENDPOINTS) - {
            ("POST", "/organizations/"),
            ("PATCH", "/organizations/{slug}"),
            ("DELETE", "/organizations/{organization_slug}/members/{member_uuid}"),
            ("PATCH", "/admin/organizations/{organization_uuid}/status"),
        }
        assert _route_endpoints(app) == expected

    def test_disable_admin_group_even_when_admin_configured(self):
        app = FastAPI()
        _make_organizations(with_admin=True).init_app(
            app,
            routes=OrganizationsRoutesConfig(admin=False, member=False),
        )

        assert _route_endpoints(app) == {
            ("POST", "/organizations/"),
            ("GET", "/organizations/"),
            ("GET", "/organizations/{slug}"),
            ("PATCH", "/organizations/{slug}"),
        }

    def test_allow_list_admin_org_routes_only(self):
        app = FastAPI()
        _make_organizations(with_admin=True).init_app(
            app,
            prefix="/api/v1",
            routes=OrganizationsRoutesConfig(
                default=False,
                admin=AdminOrganizationRoutesConfig(default=False, list=True),
            ),
        )

        assert _route_endpoints(app) == {("GET", "/api/v1/admin/organizations")}

    def test_invalid_routes_argument_raises_type_error(self):
        app = FastAPI()
        with pytest.raises(TypeError):
            _make_organizations().init_app(app, routes=123)  # type: ignore[arg-type]


class TestAdminRoutesConfig:
    @pytest.mark.parametrize("routes", [None, True, AdminRoutesConfig()])
    def test_defaults_register_all_admin_routes(self, routes):
        app = FastAPI()
        _make_admin().init_app(app, routes=routes)
        assert _route_endpoints(app) == ALL_ADMIN_ENDPOINTS

    @pytest.mark.parametrize("routes", [False, AdminRoutesConfig.disabled()])
    def test_disable_all_admin_routes_keeps_exceptions(self, routes):
        app = FastAPI()
        _make_admin().init_app(app, routes=routes)

        assert _route_endpoints(app) == set()
        assert DomainException in app.exception_handlers

    def test_disable_role_group(self):
        app = FastAPI()
        _make_admin().init_app(app, routes=AdminRoutesConfig(role=False))

        assert _route_endpoints(app) == {
            ("POST", "/admin/login"),
            ("POST", "/admin/logout"),
            ("GET", "/admin/me"),
            ("GET", "/admin/users"),
        }

    def test_disable_individual_admin_and_role_endpoints(self):
        app = FastAPI()
        _make_admin().init_app(
            app,
            routes=AdminRoutesConfig(
                admin=AdminCoreRoutesConfig(list_users=False),
                role=AdminRoleRoutesConfig(
                    delete_role=False,
                    revoke_admin_role=False,
                ),
            ),
        )

        expected = ALL_ADMIN_ENDPOINTS - {
            ("GET", "/admin/users"),
            ("DELETE", "/admin/roles/{role_uuid}"),
            ("DELETE", "/admin/admins/{admin_uuid}/roles/{role_uuid}"),
        }
        assert _route_endpoints(app) == expected

    async def test_allow_list_mode_with_admin_policy_and_http_dispatch(self):
        policy = AdminPolicy(
            rules=[
                EndpointRule("GET", "/admin/me", required_role="superadmin"),
                EndpointRule("GET", "/admin/roles", required_role="superadmin"),
            ]
        )
        app = FastAPI()
        _make_admin(policy=policy).init_app(
            app,
            routes=AdminRoutesConfig(
                default=False,
                admin=AdminCoreRoutesConfig(default=False, login=True, me=True),
                role=AdminRoleRoutesConfig(default=False, list_roles=True),
            ),
        )

        assert _route_endpoints(app) == {
            ("POST", "/admin/login"),
            ("GET", "/admin/me"),
            ("GET", "/admin/roles"),
        }

        # Disabled route returns 404; disabled method on an enabled path returns 405.
        assert await _asgi_status(app, "GET", "/admin/users") == 404
        assert await _asgi_status(app, "POST", "/admin/roles") == 405
        # Enabled routes are dispatched normally (not 404/405).
        assert await _asgi_status(app, "GET", "/admin/me") == 400
        assert await _asgi_status(app, "GET", "/admin/roles") == 400

    async def test_disabled_auth_routes_return_404_over_http(self):
        app = FastAPI()
        _make_auth().init_app(
            app,
            routes=AuthRoutesConfig(
                oauth=False,
                user=AuthUserRoutesConfig(register=False),
            ),
        )

        assert await _asgi_status(app, "POST", "/auth/register") == 404
        assert await _asgi_status(app, "GET", "/auth/oauth/login/google") == 404
        # Enabled route reaches FastAPI validation (422) rather than 404.
        assert await _asgi_status(app, "POST", "/auth/login") == 422

    def test_invalid_routes_argument_raises_type_error(self):
        app = FastAPI()
        with pytest.raises(TypeError):
            _make_admin().init_app(app, routes=AuthRoutesConfig())  # type: ignore[arg-type]
