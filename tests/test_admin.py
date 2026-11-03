from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry

from gt.admin import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    DEFAULT_ROLES_PERMISSIONS,
    PERMISSION_KEYS_ENUM,
    Admin,
    AdminRegisterSchema,
)
from gt.admin.schemas import AdminListQuerySchema
from gt.admin.services import get_admin_service, get_role_service
from gt.exceptions import ConflictException, InvalidException


def make_admin(models, *, admin_id: int = 1, email: str = "admin@example.com"):
    admin = models["admin_model"](
        email=email,
        full_name="Admin User",
        avatar_bg="#ffffff",
    )
    admin.id = admin_id
    return admin


def make_fresh_base():
    class Base(DeclarativeBase):
        registry = registry()

    return Base


class TestAdminSeeders:
    def test_default_permissions_contains_wildcard_and_enum_keys(self):
        keys = [item["key"] for item in DEFAULT_PERMISSIONS]
        assert keys[0] == "*"
        for enum_key in PERMISSION_KEYS_ENUM:
            assert enum_key.value in keys

    def test_default_roles_and_permissions_mapping(self):
        role_slugs = [role["slug"] for role in DEFAULT_ROLES]
        assert "superadmin" in role_slugs
        assert "admin" in role_slugs
        assert "viewer" in role_slugs
        assert DEFAULT_ROLES_PERMISSIONS["superadmin"] == ["*"]
        assert (
            PERMISSION_KEYS_ENUM.ADMIN_VIEW.value in DEFAULT_ROLES_PERMISSIONS["viewer"]
        )
        assert (
            PERMISSION_KEYS_ENUM.ROLE_VIEW.value in DEFAULT_ROLES_PERMISSIONS["viewer"]
        )


class TestAdminModel:
    def test_defaults(self, models):
        admin = make_admin(models)

        assert admin.__tablename__ == "sys_admins"
        assert admin.status == "active"
        assert admin.is_onboarded is False
        assert admin.avatar is None
        assert admin.email_verified_at is None
        assert admin.hashed_password is None
        assert not hasattr(admin, "role")

    def test_is_active(self, models):
        admin = make_admin(models)
        assert admin.is_active() is True

        admin.status = "inactive"
        assert admin.is_active() is False

    def test_is_email_verified(self, models):
        from datetime import UTC, datetime

        admin = make_admin(models)
        assert admin.is_email_verified() is False

        admin.email_verified_at = datetime.now(UTC)
        assert admin.is_email_verified() is True


class TestAdminRegisterSchema:
    def test_derives_full_name_from_email(self):
        schema = AdminRegisterSchema(
            email="jane.doe@example.com", password="password123"
        )
        assert schema.full_name == "Jane Doe"
        assert schema.avatar_bg is not None

    def test_keeps_provided_full_name(self):
        schema = AdminRegisterSchema(
            email="jane@example.com",
            password="password123",
            full_name="Custom Name",
        )
        assert schema.full_name == "Custom Name"

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError):
            AdminRegisterSchema(email="jane@example.com", password="short")


class TestAdminListQuerySchema:
    def test_defaults(self):
        query = AdminListQuerySchema()
        assert query.limit == 20
        assert query.offset == 0
        assert query.search is None
        assert query.status is None

    def test_rejects_limit_above_max(self):
        with pytest.raises(ValidationError):
            AdminListQuerySchema(limit=101)

    def test_rejects_negative_offset(self):
        with pytest.raises(ValidationError):
            AdminListQuerySchema(offset=-1)


class TestAdminService:
    async def test_register_admin_hashes_password_and_normalizes_email(self, models):
        hash_service = MagicMock()
        hash_service.hash.return_value = "hashed-password"
        role_service = MagicMock()
        role_service.seed_default_roles_and_assign_role = AsyncMock()
        service = get_admin_service(
            session=MagicMock(),
            model=models["admin_model"],
            hash_service=hash_service,
            role_service=role_service,
        )

        def assign_id(admin):
            admin.id = 42
            return admin

        service._repository.get_by = AsyncMock(return_value=None)
        service._repository.add = AsyncMock(side_effect=assign_id)

        created = await service.register_admin(
            email="Admin@Example.COM",
            password="password123",
        )

        assert created.email == "admin@example.com"
        assert created.full_name == "Admin"
        assert created.hashed_password == "hashed-password"
        assert created.avatar_bg is not None
        hash_service.hash.assert_called_once_with("password123")
        role_service.seed_default_roles_and_assign_role.assert_awaited_once_with(
            admin_id=42,
            role_slug="superadmin",
        )

    async def test_register_admin_seeds_default_roles_and_assigns_superadmin(
        self, models
    ):
        hash_service = MagicMock()
        hash_service.hash.return_value = "hashed-password"

        role_service = get_role_service(
            session=MagicMock(),
            role_model=models["role_model"],
            admin_role_model=models["admin_role_model"],
            admin_model=models["admin_model"],
        )

        stored_roles: dict[str, Any] = {}
        next_role_id = 1

        async def get_role_by(**kwargs):
            if "slug" in kwargs:
                return stored_roles.get(kwargs["slug"])
            if "name" in kwargs:
                for r in stored_roles.values():
                    if getattr(r, "name", None) == kwargs["name"]:
                        return r
            return None

        async def add_role(role):
            nonlocal next_role_id
            role.id = next_role_id
            next_role_id += 1
            stored_roles[role.slug] = role
            return role

        role_service._role_repository.get_by = AsyncMock(side_effect=get_role_by)
        role_service._role_repository.add = AsyncMock(side_effect=add_role)
        role_service._admin_role_repository.get_by = AsyncMock(return_value=None)

        assigned_records = []

        async def add_assignment(assignment):
            assignment.id = 1
            assigned_records.append(assignment)
            return assignment

        role_service._admin_role_repository.add = AsyncMock(side_effect=add_assignment)

        service = get_admin_service(
            session=MagicMock(),
            model=models["admin_model"],
            hash_service=hash_service,
            role_service=role_service,
        )

        def assign_admin_id(admin):
            admin.id = 7
            return admin

        service._repository.get_by = AsyncMock(return_value=None)
        service._repository.add = AsyncMock(side_effect=assign_admin_id)

        created = await service.register_admin(
            email="root@example.com",
            password="password123",
        )

        assert created.id == 7
        assert set(stored_roles.keys()) == {"superadmin", "admin", "viewer"}
        superadmin_role = stored_roles["superadmin"]
        assert superadmin_role.permissions == ["*"]
        assert superadmin_role.is_system is True
        assert superadmin_role.has_permission("admin.manage") is True
        assert len(assigned_records) == 1
        assert assigned_records[0].admin_id == 7
        assert assigned_records[0].role_id == superadmin_role.id

    async def test_register_admin_duplicate_email(self, models):
        service = get_admin_service(
            session=MagicMock(),
            model=models["admin_model"],
            hash_service=MagicMock(),
        )
        service._repository.get_by = AsyncMock(return_value=make_admin(models))

        with pytest.raises(ConflictException):
            await service.register_admin(
                email="admin@example.com",
                password="password123",
            )

    async def test_get_admin_by(self, models):
        service = get_admin_service(
            session=MagicMock(),
            model=models["admin_model"],
            hash_service=MagicMock(),
        )
        admin = make_admin(models)
        service._repository.get_by = AsyncMock(return_value=admin)

        assert await service.get_admin_by(email="admin@example.com") is admin

    async def test_list_admins(self, models):
        service = get_admin_service(
            session=MagicMock(),
            model=models["admin_model"],
            hash_service=MagicMock(),
        )
        admins = [make_admin(models), make_admin(models, email="other@example.com")]
        service._repository.paginate = AsyncMock(return_value=(admins, 2))

        result, total = await service.list_admins(limit=10, offset=0)

        assert result == admins
        assert total == 2
        service._repository.paginate.assert_awaited_once_with(
            limit=10,
            offset=0,
            search=None,
            status=None,
        )


class TestRoleService:
    def make_service(self, models):
        return get_role_service(
            session=MagicMock(),
            role_model=models["role_model"],
            admin_role_model=models["admin_role_model"],
            admin_model=models["admin_model"],
        )

    async def test_create_role_rejects_unknown_permission(self, models):
        service = self.make_service(models)
        with pytest.raises(InvalidException):
            await service.create_role(
                name="Custom Role",
                permissions=["unknown.permission"],
            )

    async def test_update_system_role_protects_permissions_and_status(self, models):
        service = self.make_service(models)
        sys_role = models["role_model"](
            name="superadmin",
            slug="superadmin",
            description="Superadmin",
            permissions=["*"],
            is_system=True,
            status="active",
        )
        sys_role.id = 1
        service._role_repository.get_by = AsyncMock(return_value=sys_role)

        with pytest.raises(ConflictException):
            await service.update_role(
                role_uuid=sys_role.uuid,
                permissions=["admin.view"],
            )

        with pytest.raises(ConflictException):
            await service.update_role(
                role_uuid=sys_role.uuid,
                status="inactive",
            )

    async def test_revoke_last_superadmin_raises_conflict(self, models):
        service = self.make_service(models)
        admin = make_admin(models, admin_id=1)
        sys_role = models["role_model"](
            name="superadmin",
            slug="superadmin",
            description="Superadmin",
            permissions=["*"],
            is_system=True,
            status="active",
        )
        sys_role.id = 10
        assignment = models["admin_role_model"](admin_id=1, role_id=10)

        service._admin_repository.get_by = AsyncMock(return_value=admin)
        service._role_repository.get_by = AsyncMock(return_value=sys_role)
        service._admin_role_repository.get_by = AsyncMock(return_value=assignment)
        service._admin_role_repository.count_by_role_id = AsyncMock(return_value=1)

        with pytest.raises(ConflictException):
            await service.revoke_role_from_admin(
                admin_uuid=admin.uuid,
                role_uuid=sys_role.uuid,
            )


class TestAdminInitApp:
    def test_registers_routes_with_prefix(self):
        from fastapi import FastAPI

        admin = Admin(
            base=make_fresh_base(),
            session_factory=async_sessionmaker[AsyncSession](),
            current_admin=lambda: None,
        )
        app = FastAPI()
        admin.init_app(app, prefix="/api/v1")

        paths = set(app.openapi()["paths"])

        assert "/api/v1/admin/me" in paths
        assert "/api/v1/admin/users" in paths
        assert "/api/v1/admin/roles" in paths
        assert "/api/v1/admin/permissions" in paths
        assert "/api/v1/admin/register" not in paths

    def test_registers_routes_without_prefix(self):
        from fastapi import FastAPI

        admin = Admin(
            base=make_fresh_base(),
            session_factory=async_sessionmaker[AsyncSession](),
            current_admin=lambda: None,
        )
        app = FastAPI()
        admin.init_app(app)

        paths = set(app.openapi()["paths"])

        assert "/admin/me" in paths
        assert "/admin/users" in paths
        assert "/admin/roles" in paths
        assert "/admin/permissions" in paths
        assert "/admin/register" not in paths

    def test_exposes_service_registry_with_role_service_wired(self):
        admin = Admin(
            base=make_fresh_base(),
            session_factory=async_sessionmaker[AsyncSession](),
        )
        services = admin.get_services(MagicMock())

        assert services.admin is services.admin
        assert services.role is not None
        assert services.admin._role_service is services.role
