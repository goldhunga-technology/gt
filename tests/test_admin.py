from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry

from gt.admin import Admin, AdminRegisterSchema
from gt.admin.schemas import AdminListQuerySchema
from gt.admin.services import get_admin_service
from gt.exceptions import ConflictException


def make_admin(models, *, email: str = "admin@example.com"):
    return models["admin_model"](
        email=email,
        full_name="Admin User",
        avatar_bg="#ffffff",
    )


def make_fresh_base():
    class Base(DeclarativeBase):
        registry = registry()

    return Base


class TestAdminModel:
    def test_defaults(self, models):
        admin = make_admin(models)

        assert admin.__tablename__ == "sys_admins"
        assert admin.status == "active"
        assert admin.is_onboarded is False
        assert admin.avatar is None
        assert admin.email_verified_at is None
        assert admin.hashed_password is None

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
        service = get_admin_service(
            session=MagicMock(),
            model=models["admin_model"],
            hash_service=hash_service,
        )

        service._repository.get_by = AsyncMock(return_value=None)
        service._repository.add = AsyncMock(side_effect=lambda admin: admin)

        created = await service.register_admin(
            email="Admin@Example.COM",
            password="password123",
        )

        assert created.email == "admin@example.com"
        assert created.full_name == "Admin"
        assert created.hashed_password == "hashed-password"
        assert created.avatar_bg is not None
        hash_service.hash.assert_called_once_with("password123")

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

        assert "/api/v1/admin/users" in paths
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

        assert "/admin/users" in paths
        assert "/admin/register" not in paths

    def test_exposes_service_registry(self):
        admin = Admin(
            base=make_fresh_base(),
            session_factory=async_sessionmaker[AsyncSession](),
        )
        services = admin.get_services(MagicMock())

        assert services.admin is services.admin
