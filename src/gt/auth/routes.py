from dataclasses import dataclass

from gt.routing import ModuleRoutesConfig, RouteGroupConfig, resolve_group


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthUserRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth`` core authentication endpoints."""

    register: bool | None = None
    login: bool | None = None
    logout: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthOAuthRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth/oauth`` endpoints."""

    login: bool | None = None
    callback: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthOnboardingRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth/onboarding`` endpoints."""

    register: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthEmailRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth`` email verification endpoints."""

    verify: bool | None = None
    resend: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthProfileRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth`` user profile endpoints."""

    update_profile: bool | None = None
    change_language: bool | None = None
    deactivate: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthPasswordRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth`` password reset endpoints."""

    forgot_password: bool | None = None
    reset_password: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthSessionRoutesConfig(RouteGroupConfig):
    """Route toggles for ``/auth/session`` endpoints."""

    current: bool | None = None
    all: bool | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class AuthRoutesConfig(ModuleRoutesConfig):
    """Configuration controlling which ``Auth`` routes are registered on ``init_app``."""

    user: bool | AuthUserRoutesConfig | None = None
    oauth: bool | AuthOAuthRoutesConfig | None = None
    onboarding: bool | AuthOnboardingRoutesConfig | None = None
    email: bool | AuthEmailRoutesConfig | None = None
    profile: bool | AuthProfileRoutesConfig | None = None
    password: bool | AuthPasswordRoutesConfig | None = None
    session: bool | AuthSessionRoutesConfig | None = None

    def resolve_user(self) -> AuthUserRoutesConfig:
        return resolve_group(
            self.user, default=self.default, group_cls=AuthUserRoutesConfig
        )

    def resolve_oauth(self) -> AuthOAuthRoutesConfig:
        return resolve_group(
            self.oauth, default=self.default, group_cls=AuthOAuthRoutesConfig
        )

    def resolve_onboarding(self) -> AuthOnboardingRoutesConfig:
        return resolve_group(
            self.onboarding,
            default=self.default,
            group_cls=AuthOnboardingRoutesConfig,
        )

    def resolve_email(self) -> AuthEmailRoutesConfig:
        return resolve_group(
            self.email, default=self.default, group_cls=AuthEmailRoutesConfig
        )

    def resolve_profile(self) -> AuthProfileRoutesConfig:
        return resolve_group(
            self.profile, default=self.default, group_cls=AuthProfileRoutesConfig
        )

    def resolve_password(self) -> AuthPasswordRoutesConfig:
        return resolve_group(
            self.password, default=self.default, group_cls=AuthPasswordRoutesConfig
        )

    def resolve_session(self) -> AuthSessionRoutesConfig:
        return resolve_group(
            self.session, default=self.default, group_cls=AuthSessionRoutesConfig
        )
