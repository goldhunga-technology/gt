from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING

from pydantic.main import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from gt.admin import Admin

from gt.auth.events import event_bus
from gt.auth.models._auth_user_model import TUser
from gt.organizations.adapters import get_organization_membership_check
from gt.organizations.interfaces._organization_membership_check import (
    OrganizationMembershipCheck,
)
from gt.organizations.models import (
    OrganizationMemberModelBase,
    OrganizationModel,
    TOrganization,
    TOrganizationMember,
    create_organization_member_model,
    create_organization_model,
)
from gt.organizations.schemas import OrganizationCreateSchema
from gt.organizations.services._service_registry import OrganizationServiceRegistry


class Organizations:
    """
    This class is responsible for wiring organization models, services and
    routers onto the application.
    """

    def __init__(
        self,
        *,
        base: type[DeclarativeBase],
        session_factory: async_sessionmaker[AsyncSession],
        user_model: type[TUser],
        organization_model: type[TOrganization] | None = None,
        organization_member_model: type[TOrganizationMember] | None = None,
        organization_create_schema: type[BaseModel] | None = None,
        current_user: Callable | None = None,
        user_service_factory: Callable | None = None,
        allow_multiple_organizations: bool = True,
        default_status: str = "trial",
        trial_days: int | None = 14,
        admin: "Admin | None" = None,
    ):
        """
        Initializes the Organizations class.

        Args:
            base: The declarative base class (SQLAlchemy or SQLModel).
            session_factory: The application's async session factory.
            user_model: The concrete user model class.
            organization_model: An optional custom organization model base.
            organization_member_model: An optional custom organization member model base.
            organization_create_schema: An optional custom create schema.
            current_user: A FastAPI dependency that resolves the current authenticated user.
            user_service_factory: An optional callable receiving a session and
                returning an object exposing a ``user`` service with
                ``get_user_by`` and ``get_users_by_ids`` methods. It is used
                by the member router to resolve the public ``user_uuid`` from
                API payloads into the internal integer user id. Supply it with
                the auth service registry factory, e.g.
                ``user_service_factory=auth.get_services``.
            allow_multiple_organizations: Whether users can belong to/own
                multiple organizations (defaults to True).
            default_status: Status assigned to newly created organizations.
            trial_days: Number of days a trial lasts. ``None`` disables expiry.
            admin: An optional ``Admin`` instance. When supplied, the
                administrator organization routes are registered under
                ``/admin/organizations``.
        """
        self.session_factory = session_factory
        self.user_model = user_model
        self.allow_multiple_organizations = allow_multiple_organizations
        self.default_status = default_status
        self.trial_days = trial_days
        self.admin = admin

        ## models
        self.organization_model = create_organization_model(
            base=base,
            user_model=user_model,
            model=organization_model or OrganizationModel,
        )
        self.organization_member_model = create_organization_member_model(
            base=base,
            user_model=user_model,
            organization_model=self.organization_model,
            model=organization_member_model or OrganizationMemberModelBase,
        )

        ## schemas
        self.organization_create_schema = (
            organization_create_schema or OrganizationCreateSchema
        )

        ## dependencies
        self.current_user = current_user
        self.user_service_factory = user_service_factory

        ## event bus
        self.event_bus = event_bus

    def init_app(self, app, prefix: str | None = None):
        """
        Initializes the FastAPI application with organization routes.

        Args:
            app: The FastAPI application.
            prefix: An optional path prefix prepended to every organization route.
        """
        self._register_routers(app, prefix=prefix)

    def on(self, event_type: type):
        """
        Registers an event handler for a specific event type.

        :param event_type: The type of the event to listen for.
        """

        def decorator(handler):
            self.event_bus.register(event_type, handler)
            return handler

        return decorator

    def get_services(self, session: AsyncSession) -> OrganizationServiceRegistry:
        """
        Builds a per-session OrganizationServiceRegistry with the
        organization models pre-wired.

        Access any organization service as an attribute of the returned
        registry, e.g. ``organizations.get_services(session).organization``
        or ``.member``.
        """
        return OrganizationServiceRegistry(
            session=session,
            organization_model=self.organization_model,
            member_model=self.organization_member_model,
            allow_multiple_organizations=self.allow_multiple_organizations,
            default_status=self.default_status,
            trial_days=self.trial_days,
        )

    def get_belongs_to_org_check(self) -> OrganizationMembershipCheck:
        """
        Returns the :class:`OrganizationMembershipCheck` port for the auth
        ``belongs_to_org`` policy check.

        It rejects a request when no organization exists in the database yet
        (``ORGANIZATION_NOT_SET_UP``) or when the current user is not an
        active member of any organization (``ORGANIZATION_REQUIRED``).

        Wire it into the auth policies with::

            auth.configure_belongs_to_org_check(
                organizations.get_belongs_to_org_check()
            )
        """
        return get_organization_membership_check(self)

    async def get_db_session(self) -> AsyncGenerator[AsyncSession]:
        """
        Provides a database session for use in the application.
        """
        async with self.session_factory() as session:
            yield session

    def _register_routers(self, app, prefix: str | None = None):
        """
        Registers organization-related routers to the FastAPI application.
        """
        from gt.organizations.routers import (
            create_admin_organization_router,
            create_organizations_router,
        )

        routers = create_organizations_router(organizations=self)
        if prefix:
            app.include_router(routers, prefix=prefix)
        else:
            app.include_router(routers)

        if self.admin is not None:
            admin_routers = create_admin_organization_router(
                organizations=self,
                admin=self.admin,
            )
            if prefix:
                app.include_router(admin_routers, prefix=prefix)
            else:
                app.include_router(admin_routers)
