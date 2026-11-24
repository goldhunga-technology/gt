from dataclasses import dataclass

from gt.routing import ModuleRoutesConfig, RouteGroupConfig, resolve_group


@dataclass(slots=True, frozen=True, kw_only=True)
class OrganizationRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/organizations`` endpoints."""

    create: bool | None = None
    list: bool | None = None
    get: bool | None = None
    update: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class OrganizationMemberRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/organizations/{organization_slug}/members`` endpoints."""

    add: bool | None = None
    list: bool | None = None
    update: bool | None = None
    remove: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AdminOrganizationRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/admin/organizations`` endpoints."""

    list: bool | None = None
    update_status: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class OrganizationsRoutesConfig(ModuleRoutesConfig):
    """Configuration controlling which ``Organizations`` routes are registered on ``init_app``."""

    organization: bool | OrganizationRoutesConfig | None = None
    member: bool | OrganizationMemberRoutesConfig | None = None
    admin: bool | AdminOrganizationRoutesConfig | None = None

    def resolve_organization(self) -> OrganizationRoutesConfig:
        return resolve_group(
            self.organization,
            default=self.default,
            group_cls=OrganizationRoutesConfig,
        )

    def resolve_member(self) -> OrganizationMemberRoutesConfig:
        return resolve_group(
            self.member,
            default=self.default,
            group_cls=OrganizationMemberRoutesConfig,
        )

    def resolve_admin(self) -> AdminOrganizationRoutesConfig:
        return resolve_group(
            self.admin,
            default=self.default,
            group_cls=AdminOrganizationRoutesConfig,
        )
