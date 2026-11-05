from gt.exceptions import DomainException
from gt.organizations.interfaces._organization_membership_check import (
    OrganizationMembershipCheck,
)


class OrganizationMembershipCheckImpl(OrganizationMembershipCheck):
    """
    Implementation of the organization membership check port.
    """

    def __init__(self, organizations):
        """
        Args:
            organizations: An initialized ``gt.organizations.Organizations``
                instance used to resolve membership.
        """
        self._organizations = organizations

    async def check_user_belongs_to_organization(self, *, user, session) -> None:
        """Reject when no organization is set up or the user is not a member."""
        services = self._organizations.get_services(session)

        if not await services.organization.is_any_organization_setup():
            raise DomainException(
                error="Organization is not set up.",
                errors={"code": "ORGANIZATION_NOT_SET_UP"},
            )

        membership = await services.member.get_member_by(user_id=user.id)
        if not membership or not membership.is_active():
            raise DomainException(
                error="Organization is required.",
                errors={"code": "ORGANIZATION_REQUIRED"},
            )

        organization = await services.organization.get_organization_by(
            id=membership.organization_id
        )
        if not organization or not organization.is_active():
            raise DomainException(
                error="Organization is inactive.",
                errors={"code": "ORGANIZATION_INACTIVE"},
            )


def get_organization_membership_check(organizations) -> OrganizationMembershipCheckImpl:
    """
    Factory function to create an OrganizationMembershipCheckImpl instance.
    """
    return OrganizationMembershipCheckImpl(organizations)
