from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, registry

from gt.auth.models._auth_user_model import create_auth_user_model
from gt.exceptions import ConflictException, DomainException
from gt.organizations import Organizations
from gt.organizations.models import OrganizationStatus, generate_slug
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


class TestOrganizationStatus:
    def test_active_trial_is_usable(self, models):
        org = make_organization(models)
        org.status = OrganizationStatus.TRIAL.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=1)

        assert org.effective_status() is OrganizationStatus.TRIAL
        assert org.is_active() is True

    def test_expired_trial_is_inactive(self, models):
        org = make_organization(models)
        org.status = OrganizationStatus.TRIAL.value
        org.trial_ends_at = datetime.now(UTC) - timedelta(days=1)

        assert org.effective_status() is OrganizationStatus.INACTIVE
        assert org.is_active() is False


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


class TestOrganizationStatusTransitions:
    async def test_trial_to_active(self, models):
        service = get_organization_service(
            session=MagicMock(), model=models["organization_model"]
        )
        org = make_organization(models)
        org.status = OrganizationStatus.TRIAL.value
        service._repository.update = AsyncMock(return_value=org)

        result = await service.change_status(
            organization=org,
            new_status=OrganizationStatus.ACTIVE.value,
            actor_id=1,
            reason="Paid",
        )

        assert result.status == OrganizationStatus.ACTIVE.value
        assert result.status_changed_by == 1
        assert result.status_reason == "Paid"

    async def test_invalid_transition_is_rejected(self, models):
        service = get_organization_service(
            session=MagicMock(), model=models["organization_model"]
        )
        org = make_organization(models)

        with pytest.raises(ConflictException) as exc:
            await service.change_status(
                organization=org,
                new_status=OrganizationStatus.TRIAL.value,
            )

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "INVALID_STATUS_TRANSITION"

    async def test_expire_trials_persists_inactive(self, models):
        service = get_organization_service(
            session=MagicMock(), model=models["organization_model"]
        )
        org = make_organization(models)
        org.status = OrganizationStatus.TRIAL.value
        org.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        service._repository.filter_by = AsyncMock(return_value=[org])
        service._repository.update = AsyncMock(return_value=org)

        expired = await service.expire_trials()

        assert expired == 1
        assert org.status == OrganizationStatus.INACTIVE.value
        assert org.status_reason == "Trial expired."

    async def test_list_organizations(self, models):
        service = get_organization_service(
            session=MagicMock(), model=models["organization_model"]
        )
        org = make_organization(models)
        service._repository.paginate = AsyncMock(return_value=([org], 1))

        organizations, total = await service.list_organizations(limit=10)

        assert organizations == [org]
        assert total == 1

    async def test_get_organization_stats(self, models):
        service = get_organization_service(
            session=MagicMock(), model=models["organization_model"]
        )
        service._repository.count_by_status = AsyncMock(
            return_value={"active": 3, "trial": 2, "inactive": 1}
        )

        stats = await service.get_organization_stats()

        assert stats == {
            "total": 6,
            "active": 3,
            "trial": 2,
            "inactive": 1,
            "cancelled": 0,
        }

    async def test_count_members_by_organization_ids(self, models):
        service = get_organization_member_service(
            session=MagicMock(), model=models["organization_member_model"]
        )
        service._repository.count_by_organization_ids = AsyncMock(
            return_value={1: 5, 2: 3}
        )

        counts = await service.count_members_by_organization_ids([1, 2])

        assert counts == {1: 5, 2: 3}


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
    def make_resolver(self, *, org_exists=True, membership=None, organization=None):
        class Base(DeclarativeBase):
            registry = registry()

        user_model = create_auth_user_model(Base)
        organizations = Organizations(
            base=Base,
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=user_model,
        )

        if organization is None:
            organization = MagicMock()
            organization.is_active.return_value = True

        services = MagicMock()
        services.organization.is_any_organization_setup = AsyncMock(
            return_value=org_exists
        )
        services.organization.get_organization_by = AsyncMock(return_value=organization)
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

    async def test_raises_when_organization_inactive(self, models):
        member = make_member(models)
        organization = make_organization(models)
        organization.status = OrganizationStatus.INACTIVE.value
        check = self.make_resolver(
            org_exists=True, membership=member, organization=organization
        )

        with pytest.raises(DomainException) as exc:
            await check.check_user_belongs_to_organization(
                user=MagicMock(id=member.user_id), session=MagicMock()
            )

        assert exc.value.errors is not None
        assert exc.value.errors["code"] == "ORGANIZATION_INACTIVE"


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


class TestAdminOrganizationRoutes:
    def test_registers_admin_organization_routes(self):
        from fastapi import FastAPI

        from gt.admin import Admin

        class Base(DeclarativeBase):
            registry = registry()

        user_model = create_auth_user_model(Base)
        admin = Admin(
            base=Base,
            session_factory=async_sessionmaker[AsyncSession](),
            current_admin=lambda: None,
        )
        organizations = Organizations(
            base=Base,
            session_factory=async_sessionmaker[AsyncSession](),
            user_model=user_model,
            admin=admin,
        )

        app = FastAPI()
        organizations.init_app(app, prefix="/api/v1")

        paths = set(app.openapi()["paths"])
        assert "/api/v1/admin/organizations" in paths
        assert "/api/v1/admin/organizations/{organization_uuid}/status" in paths
