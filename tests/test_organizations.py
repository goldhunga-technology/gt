from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry

from gt.auth.models._auth_user_model import create_auth_user_model
from gt.exceptions import ConflictException, DomainException
from gt.organizations import Organizations
from gt.organizations.models import generate_slug
from gt.organizations.schemas import OrganizationCreateSchema
from gt.organizations.services import (
    get_organization_member_service,
    get_organization_service,
)


def make_organization(models, *, owner_id: int = 1, name: str = "My Org"):
    return models["organization_model"](
        name=name.lower(),
        slug=generate_slug(name),
        owner_id=owner_id,
    )


def make_member(
    models, *, organization_id: int = 1, user_id: int = 2, role: str = "member"
):
    return models["organization_member_model"](
        organization_id=organization_id, user_id=user_id, role=role
    )


class TestGenerateSlug:
    def test_converts_whitespace_to_hyphens(self):
        assert generate_slug("My Test Org") == "my-test-org"

    def test_lowercases_and_strips_special_chars(self):
        assert generate_slug("  Goldhunga's Tech!!  ") == "goldhungas-tech"

    def test_collapses_multiple_hyphens(self):
        assert generate_slug("A   B") == "a-b"


class TestOrganizationModel:
    def test_name_and_slug(self, models):
        org = make_organization(models)
        assert org.name == "my org"
        assert org.slug == "my-org"

    def test_is_active(self, models):
        assert make_organization(models, name="Active Org").is_active() is True

    def test_default_status_active(self, models):
        org = make_organization(models)
        assert org.status == "active"


class TestOrganizationMemberModel:
    def test_fields(self, models):
        member = make_member(models)
        assert member.organization_id == 1
        assert member.user_id == 2
        assert member.status == "active"
        assert member.role == "member"
        assert member.is_active() is True

    def test_owner_role(self, models):
        member = make_member(models, role="owner")
        assert member.role == "owner"


class TestOrganizationCreateSchema:
    def test_name_stored_lowercase(self):
        schema = OrganizationCreateSchema(name="  My Cool Org  ")
        assert schema.name == "my cool org"


class TestOrganizationService:
    async def test_create_organization(self, models):
        model = models["organization_model"]
        service = get_organization_service(session=MagicMock(), model=model)

        repository = service._repository
        repository.add = AsyncMock(
            return_value=make_organization(models, name="New Org")
        )
        repository.get_by = AsyncMock(return_value=None)

        result = await service.create_organization(name="New Org", owner_id=1)

        assert result.name == "new org"
        assert result.slug == "new-org"

    async def test_create_organization_duplicate_name(self, models):
        model = models["organization_model"]
        service = get_organization_service(session=MagicMock(), model=model)

        repository = service._repository
        repository.get_by = AsyncMock(return_value=make_organization(models))

        with pytest.raises(ConflictException):
            await service.create_organization(name="My Org", owner_id=1)

    async def test_get_organization_by(self, models):
        model = models["organization_model"]
        service = get_organization_service(session=MagicMock(), model=model)

        service._repository.get_by = AsyncMock(return_value=make_organization(models))

        result = await service.get_organization_by(slug="my-org")
        assert result is not None
        assert result.slug == "my-org"

    async def test_is_any_organization_setup(self, models):
        model = models["organization_model"]
        service = get_organization_service(session=MagicMock(), model=model)

        service._repository.get_first = AsyncMock(return_value=None)
        assert await service.is_any_organization_setup() is False

        service._repository.get_first = AsyncMock(
            return_value=make_organization(models)
        )
        assert await service.is_any_organization_setup() is True

    async def test_get_organization_by_user_id(self, models):
        service = get_organization_service(
            session=MagicMock(),
            model=models["organization_model"],
            member_model=models["organization_member_model"],
        )

        service._repository.get_by = AsyncMock(return_value=make_organization(models))
        assert service._member_repository is not None
        service._member_repository.filter_by = AsyncMock(
            return_value=[make_member(models, user_id=2)]
        )

        result = await service.get_organization_by_user_id(user_id=2)

        assert result is not None
        assert result.slug == "my-org"

    async def test_get_organization_by_user_id_returns_none_when_no_membership(
        self, models
    ):
        service = get_organization_service(
            session=MagicMock(),
            model=models["organization_model"],
            member_model=models["organization_member_model"],
        )

        assert service._member_repository is not None
        service._member_repository.filter_by = AsyncMock(return_value=[])

        assert await service.get_organization_by_user_id(user_id=2) is None


class TestOrganizationMemberService:
    async def test_add_member(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        service._repository.get_by = AsyncMock(return_value=None)
        service._repository.add = AsyncMock(return_value=make_member(models))

        result = await service.add_member(
            organization_id=1, organization_uuid="test-uuid", user_id=2
        )
        assert result.organization_id == 1
        assert result.user_id == 2
        assert result.role == "member"

    async def test_add_member_with_role(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        service._repository.get_by = AsyncMock(return_value=None)
        service._repository.add = AsyncMock(
            return_value=make_member(models, role="admin")
        )

        result = await service.add_member(
            organization_id=1, organization_uuid="test-uuid", user_id=2, role="admin"
        )
        assert result.role == "admin"

    async def test_add_member_duplicate(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        service._repository.get_by = AsyncMock(return_value=make_member(models))

        with pytest.raises(ConflictException):
            await service.add_member(
                organization_id=1, organization_uuid="test-uuid", user_id=2
            )

    async def test_list_members(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        service._repository.filter_by = AsyncMock(
            return_value=[make_member(models), make_member(models, user_id=3)]
        )

        result = await service.list_members(organization_id=1)
        assert len(result) == 2

    async def test_update_member(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        member = make_member(models)
        service._repository.update = AsyncMock(return_value=member)

        result = await service.update_member(
            member=member, organization_uuid="test-uuid", status="inactive"
        )
        assert result.status == "inactive"

    async def test_update_member_role(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        member = make_member(models)
        service._repository.update = AsyncMock(return_value=member)

        result = await service.update_member(
            member=member, organization_uuid="test-uuid", role="admin"
        )
        assert result.role == "admin"

    async def test_remove_member_missing_raises(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(session=MagicMock(), model=model)

        with pytest.raises(DomainException):
            await service.remove_member(None, organization_uuid="test-uuid")


class TestBelongsToOrgCheck:
    def make_resolver(self, *, org_exists=True, membership=None):
        class Base(DeclarativeBase):
            registry = registry()

        user_model = create_auth_user_model(Base)
        organizations = Organizations(
            base=Base,
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=user_model,
        )

        services = MagicMock()
        services.organization.is_any_organization_setup = AsyncMock(
            return_value=org_exists
        )
        services.member.get_member_by = AsyncMock(return_value=membership)
        organizations.get_services = MagicMock(return_value=services)

        return organizations.get_belongs_to_org_check()

    async def test_raises_when_no_organizations(self):
        check = self.make_resolver(org_exists=False)

        with pytest.raises(DomainException) as exc:
            await check.check_user_belongs_to_organization(
                user=MagicMock(), session=MagicMock()
            )

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ORGANIZATION_NOT_SET_UP"

    async def test_raises_when_not_member(self):
        check = self.make_resolver(org_exists=True, membership=None)

        with pytest.raises(DomainException) as exc:
            await check.check_user_belongs_to_organization(
                user=MagicMock(), session=MagicMock()
            )

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ORGANIZATION_REQUIRED"

    async def test_raises_when_inactive_member(self, models):
        member = make_member(models)
        member.status = "inactive"
        check = self.make_resolver(org_exists=True, membership=member)

        with pytest.raises(DomainException) as exc:
            await check.check_user_belongs_to_organization(
                user=MagicMock(id=member.user_id), session=MagicMock()
            )

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ORGANIZATION_REQUIRED"

    async def test_passes_when_active_member(self, models):
        member = make_member(models)
        check = self.make_resolver(org_exists=True, membership=member)

        result = await check.check_user_belongs_to_organization(
            user=MagicMock(id=member.user_id), session=MagicMock()
        )

        assert result is None


class TestAllowMultipleOrganizationsConfig:
    def test_default_allow_multiple_organizations_is_true(self):
        class Base(DeclarativeBase):
            registry = registry()

        user_model = create_auth_user_model(Base)
        organizations = Organizations(
            base=Base,
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=user_model,
        )
        assert organizations.allow_multiple_organizations is True

    def test_custom_allow_multiple_organizations_is_false(self):
        class Base(DeclarativeBase):
            registry = registry()

        user_model = create_auth_user_model(Base)
        organizations = Organizations(
            base=Base,
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=user_model,
            allow_multiple_organizations=False,
        )
        assert organizations.allow_multiple_organizations is False

    async def test_create_org_blocked_when_single_org_enforced(self, models):
        model = models["organization_model"]
        member_model = models["organization_member_model"]
        service = get_organization_service(
            session=MagicMock(),
            model=model,
            member_model=member_model,
            allow_multiple_organizations=False,
        )
        service._repository.filter_by = AsyncMock(
            return_value=[make_organization(models, owner_id=1)]
        )

        with pytest.raises(ConflictException) as exc:
            await service.create_organization(name="Second Org", owner_id=1)

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "SINGLE_ORGANIZATION_LIMIT_EXCEEDED"

    async def test_add_member_blocked_when_single_org_enforced(self, models):
        model = models["organization_member_model"]
        service = get_organization_member_service(
            session=MagicMock(), model=model, allow_multiple_organizations=False
        )
        service._repository.filter_by = AsyncMock(
            return_value=[make_member(models, user_id=2)]
        )

        with pytest.raises(ConflictException) as exc:
            await service.add_member(
                organization_id=2, organization_uuid="org-2-uuid", user_id=2
            )

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "SINGLE_ORGANIZATION_LIMIT_EXCEEDED"
