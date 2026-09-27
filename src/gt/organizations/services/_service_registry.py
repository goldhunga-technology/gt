from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OrganizationMemberModelBase, OrganizationModel
from ._organization_member_service import get_organization_member_service
from ._organization_service import get_organization_service


class OrganizationServiceRegistry:
    """
    Per-session access to every organization service with the models pre-wired.

    Build one per request via ``organizations.get_services(session)`` and access
    the services you need as attributes. Each service is created lazily and
    cached for the lifetime of the registry.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        organization_model: type[OrganizationModel],
        member_model: type[OrganizationMemberModelBase],
        allow_multiple_organizations: bool = True,
    ):
        self._session = session
        self._organization_model = organization_model
        self._member_model = member_model
        self._allow_multiple_organizations = allow_multiple_organizations

    @cached_property
    def organization(self):
        """Service for organization operations."""
        return get_organization_service(
            session=self._session,
            model=self._organization_model,
            member_model=self._member_model,
            allow_multiple_organizations=self._allow_multiple_organizations,
        )

    @cached_property
    def member(self):
        """Service for organization member operations."""
        return get_organization_member_service(
            session=self._session,
            model=self._member_model,
            allow_multiple_organizations=self._allow_multiple_organizations,
        )
