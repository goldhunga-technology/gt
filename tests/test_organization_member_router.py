import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry

from gt.exceptions import DomainException
from gt.organizations import Organizations
from gt.organizations.routers._organization_member_router import (
    _get_user_service,
    _member_payload,
    _resolve_user_by_uuid,
    _resolve_user_uuids,
    create_organization_member_router,
)
from gt.organizations.schemas import (
    OrganizationMemberAddSchema,
    OrganizationMemberResponseSchema,
)

USER_UUID_UPPER = "3F6A0000-0000-4000-8000-000000000000"
USER_UUID_LOWER = USER_UUID_UPPER.lower()


def _make_fresh_base():
    class Base(DeclarativeBase):
        registry = registry()

    return Base


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


def make_org(*, owner_id: int = 1, org_id: int = 1):
    org = MagicMock()
    org.id = org_id
    org.uuid = "org-uuid"
    org.owner_id = owner_id
    org.slug = "my-org"
    return org


def make_member(*, user_id: int, uuid: str | None = None, role: str = "member"):
    member = MagicMock()
    member.user_id = user_id
    member.uuid = uuid or f"member-uuid-{user_id}"
    member.status = "active"
    member.role = role
    return member


def make_user(*, id: int, uuid: str | None = None):
    user = MagicMock()
    user.id = id
    user.uuid = uuid or f"user-uuid-{id}"
    return user


def make_services(*, organization, members=None):
    services = SimpleNamespace(
        organization=MagicMock(),
        member=MagicMock(),
    )
    services.organization.get_organization_by = AsyncMock(return_value=organization)
    services.member.list_members = AsyncMock(return_value=members or [])
    return services


def user_service_factory_for(user_service):
    def factory(session):
        return SimpleNamespace(user=user_service)

    return factory


def make_organizations(*, session, services, user_service_factory=None):
    def current_user():
        return None

    return SimpleNamespace(
        session_factory=make_session_factory(session),
        current_user=current_user,
        user_service_factory=user_service_factory,
        get_services=MagicMock(return_value=services),
    )


def get_endpoint(router, method: str, path: str):
    for route in router.routes:
        if route.path == path and method in (route.methods or set()):
            return route.endpoint
    raise AssertionError(f"No route {method} {path}")


def parse(response) -> dict:
    return json.loads(response.body)


class TestOrganizationMemberSchemas:
    def test_add_schema_accepts_uuid_string(self):
        schema = OrganizationMemberAddSchema(user_uuid=USER_UUID_LOWER)  # type: ignore[arg-type]
        assert str(schema.user_uuid) == USER_UUID_LOWER

    def test_add_schema_rejects_invalid_uuid(self):
        with pytest.raises(ValidationError):
            OrganizationMemberAddSchema(user_uuid="not-a-uuid")  # type: ignore[arg-type]

    def test_add_schema_requires_user_uuid(self):
        with pytest.raises(ValidationError):
            OrganizationMemberAddSchema()  # type: ignore[call-arg]

    def test_response_schema_exposes_only_uuids(self):
        fields = set(OrganizationMemberResponseSchema.model_fields)
        assert fields == {"uuid", "user_uuid", "organization_uuid", "status", "role"}
        assert "user_id" not in fields
        assert "organization_id" not in fields

    def test_member_payload_never_leaks_int_ids(self):
        payload = _member_payload(
            make_member(user_id=2),
            user_uuid="user-uuid-2",
            organization_uuid="org-uuid",
        )
        assert "user_id" not in payload
        assert "organization_id" not in payload
        assert payload["user_uuid"] == "user-uuid-2"
        assert payload["organization_uuid"] == "org-uuid"


class TestResolveUserByUuid:
    async def test_returns_user_on_success(self):
        user = make_user(id=7)
        user_service = SimpleNamespace(get_user_by=AsyncMock(return_value=user))
        resolved, error = await _resolve_user_by_uuid(
            user_service_factory_for(user_service), MagicMock(), USER_UUID_LOWER
        )
        assert error is None
        assert resolved is user

    async def test_unknown_uuid_returns_user_not_found(self):
        user_service = SimpleNamespace(get_user_by=AsyncMock(return_value=None))
        resolved, error = await _resolve_user_by_uuid(
            user_service_factory_for(user_service), MagicMock(), USER_UUID_LOWER
        )
        assert resolved is None
        assert error is not None
        assert error.status_code == 400
        assert parse(error)["errors"]["code"] == "USER_NOT_FOUND"

    async def test_missing_factory_returns_not_configured(self):
        resolved, error = await _resolve_user_by_uuid(
            None, MagicMock(), USER_UUID_LOWER
        )
        assert resolved is None
        assert error is not None
        assert error.status_code == 500
        assert parse(error)["errors"]["code"] == "USER_SERVICE_NOT_CONFIGURED"

    async def test_factory_without_get_user_by_returns_not_configured(self):
        def factory(session):
            return SimpleNamespace(user=SimpleNamespace())

        resolved, error = await _resolve_user_by_uuid(
            factory, MagicMock(), USER_UUID_LOWER
        )
        assert resolved is None
        assert error is not None
        assert parse(error)["errors"]["code"] == "USER_SERVICE_NOT_CONFIGURED"

    async def test_domain_exception_becomes_error_response(self):
        user_service = SimpleNamespace(
            get_user_by=AsyncMock(
                side_effect=DomainException(
                    error="db down", errors={"code": "DB_ERROR"}
                )
            )
        )
        resolved, error = await _resolve_user_by_uuid(
            user_service_factory_for(user_service), MagicMock(), USER_UUID_LOWER
        )
        assert resolved is None
        assert error is not None
        assert parse(error)["errors"]["code"] == "DB_ERROR"


class TestResolveUserUuids:
    async def test_empty_inputs(self):
        assert await _resolve_user_uuids(None, [make_member(user_id=2)]) == {}
        assert await _resolve_user_uuids(MagicMock(), []) == {}

    async def test_batch_lookup_single_query(self):
        users = [make_user(id=2), make_user(id=3)]
        user_service = MagicMock()
        user_service.get_users_by_ids = AsyncMock(return_value=users)
        user_service.get_user_by = AsyncMock(return_value=None)

        result = await _resolve_user_uuids(
            user_service, [make_member(user_id=2), make_member(user_id=3)]
        )

        user_service.get_users_by_ids.assert_awaited_once_with([2, 3])
        user_service.get_user_by.assert_not_awaited()
        assert result == {2: "user-uuid-2", 3: "user-uuid-3"}

    async def test_falls_back_when_batch_method_missing(self):
        users_by_id = {2: make_user(id=2), 3: make_user(id=3)}

        def get_user_by(**kwargs):
            return users_by_id[kwargs["id"]]

        user_service = SimpleNamespace(get_user_by=AsyncMock(side_effect=get_user_by))

        result = await _resolve_user_uuids(
            user_service, [make_member(user_id=2), make_member(user_id=3)]
        )

        assert result == {2: "user-uuid-2", 3: "user-uuid-3"}
        assert user_service.get_user_by.await_count == 2


class TestGetUserService:
    def test_none_factory(self):
        assert _get_user_service(None, MagicMock()) is None

    def test_returns_underlying_user_service(self):
        user_service = SimpleNamespace(get_user_by=AsyncMock())
        service = _get_user_service(user_service_factory_for(user_service), MagicMock())
        assert service is user_service


class TestOrganizationsUserServiceFactory:
    def test_stores_factory(self, models):
        def factory(session):
            return None

        organizations = Organizations(
            base=_make_fresh_base(),
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=models["user_model"],
            user_service_factory=factory,
        )
        assert organizations.user_service_factory is factory

    def test_defaults_to_none(self, models):
        organizations = Organizations(
            base=_make_fresh_base(),
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=models["user_model"],
        )
        assert organizations.user_service_factory is None


class TestMemberRouter:
    def build(self, *, members=None, user_service=None):
        session = make_session()
        services = make_services(organization=make_org(), members=members)
        organizations = make_organizations(
            session=session,
            services=services,
            user_service_factory=(
                user_service_factory_for(user_service) if user_service else None
            ),
        )
        router = create_organization_member_router(organizations=organizations)
        return router, services, user_service

    async def test_add_member_resolves_uuid_to_internal_id(self):
        user = make_user(id=7, uuid=USER_UUID_LOWER)
        member = make_member(user_id=7)
        user_service = SimpleNamespace(get_user_by=AsyncMock(return_value=user))
        router, services, _ = self.build(user_service=user_service)
        services.member.add_member = AsyncMock(return_value=member)

        endpoint = get_endpoint(router, "POST", "/{organization_slug}/members")
        response = await endpoint(
            "my-org",
            body=OrganizationMemberAddSchema(user_uuid=UUID(USER_UUID_UPPER)),
            user=MagicMock(id=1),
        )

        assert response.status_code == 200
        data = parse(response)["data"]
        assert data["uuid"] == "member-uuid-7"
        assert data["user_uuid"] == USER_UUID_LOWER
        assert data["organization_uuid"] == "org-uuid"
        assert "user_id" not in data
        assert "organization_id" not in data

        user_service.get_user_by.assert_awaited_once_with(uuid=USER_UUID_LOWER)
        assert services.member.add_member.await_args is not None
        kwargs = services.member.add_member.await_args.kwargs
        assert kwargs["user_id"] == 7
        assert kwargs["organization_id"] == 1

    async def test_add_member_unknown_uuid(self):
        user_service = SimpleNamespace(get_user_by=AsyncMock(return_value=None))
        router, services, _ = self.build(user_service=user_service)
        services.member.add_member = AsyncMock(return_value=make_member(user_id=7))

        endpoint = get_endpoint(router, "POST", "/{organization_slug}/members")
        response = await endpoint(
            "my-org",
            body=OrganizationMemberAddSchema(user_uuid=UUID(USER_UUID_LOWER)),
            user=MagicMock(id=1),
        )

        assert response.status_code == 400
        assert parse(response)["errors"]["code"] == "USER_NOT_FOUND"
        services.member.add_member.assert_not_awaited()

    async def test_add_member_without_user_service_factory(self):
        router, services, _ = self.build(user_service=None)
        services.member.add_member = AsyncMock(return_value=make_member(user_id=7))

        endpoint = get_endpoint(router, "POST", "/{organization_slug}/members")
        response = await endpoint(
            "my-org",
            body=OrganizationMemberAddSchema(user_uuid=UUID(USER_UUID_LOWER)),
            user=MagicMock(id=1),
        )

        assert response.status_code == 500
        assert parse(response)["errors"]["code"] == "USER_SERVICE_NOT_CONFIGURED"
        services.member.add_member.assert_not_awaited()

    async def test_add_member_non_owner_denied(self):
        user_service = SimpleNamespace(
            get_user_by=AsyncMock(return_value=make_user(id=7))
        )
        router, services, _ = self.build(user_service=user_service)
        services.member.add_member = AsyncMock(return_value=make_member(user_id=7))

        endpoint = get_endpoint(router, "POST", "/{organization_slug}/members")
        response = await endpoint(
            "my-org",
            body=OrganizationMemberAddSchema(user_uuid=UUID(USER_UUID_LOWER)),
            user=MagicMock(id=99),
        )

        assert parse(response)["errors"]["code"] == "ORGANIZATION_ACCESS_DENIED"
        services.member.add_member.assert_not_awaited()
        user_service.get_user_by.assert_not_awaited()

    async def test_add_member_org_not_found(self):
        router, services, _ = self.build(user_service=None)
        services.organization.get_organization_by = AsyncMock(return_value=None)
        services.member.add_member = AsyncMock(return_value=make_member(user_id=7))

        endpoint = get_endpoint(router, "POST", "/{organization_slug}/members")
        response = await endpoint(
            "my-org",
            body=OrganizationMemberAddSchema(user_uuid=UUID(USER_UUID_LOWER)),
            user=MagicMock(id=1),
        )

        assert response.status_code == 400
        assert parse(response)["errors"]["code"] == "ORGANIZATION_NOT_FOUND"
        services.member.add_member.assert_not_awaited()

    async def test_list_members_batch_resolves_uuids(self):
        members = [make_member(user_id=2), make_member(user_id=3)]
        users = [make_user(id=2), make_user(id=3)]
        user_service = MagicMock()
        user_service.get_users_by_ids = AsyncMock(return_value=users)
        user_service.get_user_by = AsyncMock(return_value=None)
        router, _services, _ = self.build(members=members, user_service=user_service)

        endpoint = get_endpoint(router, "GET", "/{organization_slug}/members")
        response = await endpoint("my-org", user=MagicMock(id=1))

        assert response.status_code == 200
        data = parse(response)["data"]
        assert [m["user_uuid"] for m in data] == ["user-uuid-2", "user-uuid-3"]
        user_service.get_users_by_ids.assert_awaited_once_with([2, 3])
        user_service.get_user_by.assert_not_awaited()

    async def test_list_members_without_factory_returns_null_uuid(self):
        members = [make_member(user_id=2)]
        router, _services, _ = self.build(members=members, user_service=None)

        endpoint = get_endpoint(router, "GET", "/{organization_slug}/members")
        response = await endpoint("my-org", user=MagicMock(id=1))

        assert response.status_code == 200
        data = parse(response)["data"]
        assert data[0]["user_uuid"] is None

    async def test_update_member_response_has_user_uuid(self):
        member = make_member(user_id=7)
        user = make_user(id=7, uuid=USER_UUID_LOWER)
        user_service = SimpleNamespace(get_user_by=AsyncMock(return_value=user))
        router, services, _ = self.build(user_service=user_service)
        services.member.get_member_by = AsyncMock(return_value=member)
        services.member.update_member = AsyncMock(return_value=member)

        endpoint = get_endpoint(
            router, "PATCH", "/{organization_slug}/members/{member_uuid}"
        )
        response = await endpoint(
            "my-org",
            member_uuid="member-uuid-7",
            body=SimpleNamespace(status="inactive", role=None),
            user=MagicMock(id=1),
        )

        assert response.status_code == 200
        data = parse(response)["data"]
        assert data["user_uuid"] == USER_UUID_LOWER
        assert data["organization_uuid"] == "org-uuid"
        assert "user_id" not in data
        user_service.get_user_by.assert_awaited_once_with(id=7)

    async def test_remove_member_returns_success(self):
        member = make_member(user_id=7)
        router, services, _ = self.build(user_service=None)
        services.member.get_member_by = AsyncMock(return_value=member)
        services.member.remove_member = AsyncMock(return_value=None)

        endpoint = get_endpoint(
            router, "DELETE", "/{organization_slug}/members/{member_uuid}"
        )
        response = await endpoint(
            "my-org", member_uuid="member-uuid-7", user=MagicMock(id=1)
        )

        assert response.status_code == 200
        services.member.remove_member.assert_awaited_once()
