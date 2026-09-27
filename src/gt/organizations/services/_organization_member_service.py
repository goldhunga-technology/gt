from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.events import event_bus
from gt.exceptions import ConflictException, DomainException, NotFoundException
from gt.organizations.events import (
    OrganizationMemberAddedEvent,
    OrganizationMemberRemovedEvent,
    OrganizationMemberUpdatedEvent,
)
from gt.organizations.models import OrganizationMemberModelBase, TOrganizationMember
from gt.organizations.repositories import OrganizationMemberRepository


class OrganizationMemberService[TOrganizationMember: OrganizationMemberModelBase]:
    """Service for managing organization member operations."""

    def __init__(
        self,
        repository: OrganizationMemberRepository[TOrganizationMember],
        model: type[TOrganizationMember],
        allow_multiple_organizations: bool = True,
    ):
        """Initialize the service with a repository and model.

        Args:
            repository: The OrganizationMemberRepository instance.
            model: The OrganizationMemberModel class.
            allow_multiple_organizations: Whether users can belong to multiple
                organizations.
        """
        self._repository = repository
        self._model = model
        self._allow_multiple_organizations = allow_multiple_organizations

    async def add_member(
        self,
        organization_id: int,
        organization_uuid: str,
        user_id: int,
        status: str = "active",
        role: str = "member",
    ) -> TOrganizationMember:
        """Add a new member to an organization.

        Args:
            organization_id: The ID of the organization.
            organization_uuid: The UUID of the organization.
            user_id: The ID of the user to add.
            status: The member status.
            role: The member role.

        Returns:
            The created member instance.

        Raises:
            ConflictException: If the user is already a member or single-organization
                limit per user is enforced.
            DomainException: On unexpected failures.
        """
        try:
            if not self._allow_multiple_organizations:
                existing_any = await self._repository.filter_by(user_id=user_id)
                if existing_any:
                    raise ConflictException(
                        error="User can only belong to one organization.",
                        errors={"code": "SINGLE_ORGANIZATION_LIMIT_EXCEEDED"},
                    )

            existing = await self._repository.get_by(
                organization_id=organization_id, user_id=user_id
            )
            if existing:
                raise ConflictException(
                    error=f"User {user_id} is already a member of organization {organization_id}.",
                )

            model_cls = cast("type[Any]", self._model)
            member = model_cls(
                organization_id=organization_id,
                user_id=user_id,
                status=status,
                role=role,
            )
            created = await self._repository.add(member)

            await event_bus.publish(
                OrganizationMemberAddedEvent(
                    member_id=created.id,
                    member_uuid=created.uuid,
                    organization_id=organization_id,
                    organization_uuid=organization_uuid,
                    user_id=user_id,
                    status=status,
                    role=role,
                )
            )

            return created
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to add organization member.",
                internal_details=str(e),
            ) from e

    async def get_member_by(self, **kwargs) -> TOrganizationMember | None:
        """Retrieve an organization member by filter criteria.

        Args:
            **kwargs: Filter keyword arguments.

        Returns:
            The matching member instance or None.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            result = await self._repository.filter_by(**kwargs)
            if len(result) > 0:
                return result[0]
            return None
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve organization member.",
                internal_details=str(e),
            ) from e

    async def list_members(self, organization_id: int) -> list[TOrganizationMember]:
        """List all members of an organization.

        Args:
            organization_id: The ID of the organization.

        Returns:
            A list of matching member instances.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.filter_by(organization_id=organization_id)
        except Exception as e:
            raise DomainException(
                error="Failed to list organization members.",
                internal_details=str(e),
            ) from e

    async def update_member(
        self,
        member: TOrganizationMember,
        organization_uuid: str,
        status: str | None = None,
        role: str | None = None,
    ) -> TOrganizationMember:
        """Update an existing organization member.

        Args:
            member: The member model instance to update.
            organization_uuid: The UUID of the organization.
            status: The new member status.
            role: The new member role.

        Returns:
            The updated member instance.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            if status is not None:
                member.status = status
            if role is not None:
                member.role = role
            updated = await self._repository.update(member)

            await event_bus.publish(
                OrganizationMemberUpdatedEvent(
                    member_id=updated.id,
                    member_uuid=updated.uuid,
                    organization_id=updated.organization_id,
                    organization_uuid=organization_uuid,
                    user_id=updated.user_id,
                    status=updated.status,
                    role=updated.role,
                )
            )

            return updated
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to update organization member.",
                internal_details=str(e),
            ) from e

    async def remove_member(
        self, member: TOrganizationMember, organization_uuid: str
    ) -> None:
        """Remove a member from an organization.

        Args:
            member: The member model instance to remove.
            organization_uuid: The UUID of the organization.

        Raises:
            NotFoundException: If the member does not exist.
            DomainException: On unexpected failures.
        """
        try:
            if not member:
                raise NotFoundException(error="Organization member not found.")

            await event_bus.publish(
                OrganizationMemberRemovedEvent(
                    member_id=member.id,
                    member_uuid=member.uuid,
                    organization_id=member.organization_id,
                    organization_uuid=organization_uuid,
                    user_id=member.user_id,
                )
            )

            await self._repository.delete(member)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to remove organization member.",
                internal_details=str(e),
            ) from e


def get_organization_member_service(
    session: AsyncSession,
    model: type[TOrganizationMember],
    allow_multiple_organizations: bool = True,
) -> OrganizationMemberService[TOrganizationMember]:
    """Factory function to create an OrganizationMemberService instance.

    Args:
        session: Async SQLAlchemy session.
        model: The OrganizationMemberModel class.
        allow_multiple_organizations: Whether users can belong to multiple
            organizations.

    Returns:
        A configured OrganizationMemberService.
    """
    repository = OrganizationMemberRepository(session=session, model=model)
    return OrganizationMemberService(
        repository=repository,
        model=model,
        allow_multiple_organizations=allow_multiple_organizations,
    )
