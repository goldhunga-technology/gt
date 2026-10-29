import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gt.admin.routers._admin_router import (
    _admin_auth_not_configured,
    create_admin_router,
)
from gt.exceptions import ServerException


def make_session():
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


def make_session_factory(session):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


def make_admin_record(*, uuid: str = "admin-uuid", email: str = "admin@example.com"):
    admin = MagicMock()
    admin.uuid = uuid
    admin.email = email
    admin.full_name = "Admin User"
    admin.avatar_bg = "#ffffff"
    admin.is_onboarded = False
    admin.status = "active"
    admin.email_verified_at = None
    admin.avatar = None
    return admin


def make_services(*, admin_service):
    return SimpleNamespace(admin=admin_service)


def make_admin(*, session, services, current_admin=None):
    return SimpleNamespace(
        session_factory=make_session_factory(session),
        current_admin=current_admin,
        get_services=MagicMock(return_value=services),
    )


def get_endpoint(router, method: str, path: str):
    for route in router.routes:
        if route.path == path and method in (route.methods or set()):
            return route.endpoint
    raise AssertionError(f"No route {method} {path}")


def parse(response) -> dict:
    return json.loads(response.body)


class TestAdminAuthGuard:
    def test_raises_when_not_configured(self):
        with pytest.raises(ServerException) as exc:
            _admin_auth_not_configured()

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ADMIN_AUTH_NOT_CONFIGURED"


class TestAdminRouter:
    def build(self, *, admin_service, current_admin=None):
        session = make_session()
        services = make_services(admin_service=admin_service)
        admin = make_admin(
            session=session,
            services=services,
            current_admin=current_admin,
        )
        router = create_admin_router(admin=admin)
        return router, admin_service

    def test_does_not_expose_register_route(self):
        admin_service = MagicMock()
        router, _ = self.build(admin_service=admin_service)

        assert all(
            getattr(route, "path", None) != "/register" for route in router.routes
        )

    async def test_list_admin_users(self):
        admin_service = MagicMock()
        admins = [
            make_admin_record(uuid="admin-1", email="one@example.com"),
            make_admin_record(uuid="admin-2", email="two@example.com"),
        ]
        admin_service.list_admins = AsyncMock(return_value=(admins, 2))
        router, _ = self.build(admin_service=admin_service)

        endpoint = get_endpoint(router, "GET", "/users")
        response = await endpoint(
            limit=10,
            offset=5,
            search="example",
            status="active",
            _current_admin=MagicMock(),
        )

        assert response.status_code == 200
        parsed = parse(response)
        assert parsed["message"] == "Admins retrieved successfully."
        assert parsed["data"]["total"] == 2
        assert parsed["data"]["limit"] == 10
        assert parsed["data"]["offset"] == 5
        assert [item["uuid"] for item in parsed["data"]["items"]] == [
            "admin-1",
            "admin-2",
        ]
        assert "hashed_password" not in parsed["data"]["items"][0]
        admin_service.list_admins.assert_awaited_once_with(
            limit=10,
            offset=5,
            search="example",
            status="active",
        )

    async def test_list_admin_users_defaults(self):
        admin_service = MagicMock()
        admin_service.list_admins = AsyncMock(return_value=([], 0))
        router, _ = self.build(admin_service=admin_service)

        endpoint = get_endpoint(router, "GET", "/users")
        response = await endpoint(
            limit=20,
            offset=0,
            search=None,
            status=None,
            _current_admin=MagicMock(),
        )

        assert response.status_code == 200
        parsed = parse(response)
        assert parsed["data"] == {
            "items": [],
            "total": 0,
            "limit": 20,
            "offset": 0,
        }
