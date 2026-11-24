from dataclasses import dataclass

from gt.routing import ModuleRoutesConfig, RouteGroupConfig, resolve_group


@dataclass(slots=True, frozen=True, kw_only=True)
class AdminCoreRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/admin`` core endpoints."""

    login: bool | None = None
    logout: bool | None = None
    me: bool | None = None
    list_users: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AdminRoleRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/admin`` role and permission endpoints."""

    list_permissions: bool | None = None
    create_role: bool | None = None
    list_roles: bool | None = None
    get_role: bool | None = None
    update_role: bool | None = None
    delete_role: bool | None = None
    list_admin_roles: bool | None = None
    assign_admin_role: bool | None = None
    revoke_admin_role: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AdminRoutesConfig(ModuleRoutesConfig):
    """Configuration controlling which ``Admin`` routes are registered on ``init_app``."""

    admin: bool | AdminCoreRoutesConfig | None = None
    role: bool | AdminRoleRoutesConfig | None = None

    def resolve_admin(self) -> AdminCoreRoutesConfig:
        return resolve_group(
            self.admin, default=self.default, group_cls=AdminCoreRoutesConfig
        )

    def resolve_role(self) -> AdminRoleRoutesConfig:
        return resolve_group(
            self.role, default=self.default, group_cls=AdminRoleRoutesConfig
        )
