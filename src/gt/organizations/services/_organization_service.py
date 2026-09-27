from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.events import event_bus
from gt.exceptions import ConflictException, DomainException
from gt.organizations.events import (
    OrganizationCreatedEvent,
    OrganizationUpdatedEvent,
)
from gt.organizations.models import OrganizationModel, TOrganization, generate_slug
from gt.organizations.repositories import (
    OrganizationMemberRepository,
    OrganizationRepository,
)


class OrganizationService[TOrganization: OrganizationModel]:
    """Service for managing organization operations."""

    def __init__(
        self,
        repository: OrganizationRepository[TOrganization],
        model: type[TOrganization],
        member_repository: OrganizationMemberRepository | None = None,
        allow_multiple_organizations: bool = True,
    ):
        """Initialize the service with a repository and model.

        Args:
            repository: The OrganizationRepository instance.
            model: The OrganizationModel class.
            member_repository: An optional OrganizationMemberRepository instance
                used to resolve organization memberships.
            allow_multiple_organizations: Whether users can belong to/own
                multiple organizations.
        """
        self._repository = repository
        self._model = model
        self._member_repository = member_repository
        self._allow_multiple_organizations = allow_multiple_organizations

    async def create_organization(
        self,
        name: str,
        owner_id: int,
        description: str | None = None,
        logo: str | None = None,
        status: str = "active",
    ) -> TOrganization:
        """Create a new organization.

        Args:
            name: The organization name (stored in lowercase).
            owner_id: The ID of the user who owns the organization.
            description: An optional organization description.
            logo: An optional organization logo.
            status: The organization status.

        Returns:
            The created organization instance.

        Raises:
            ConflictException: If an organization with the same name already exists
                or if single-organization limit per user is enforced.
            DomainException: On unexpected failures.
        """
        try:
            if not self._allow_multiple_organizations:
                owned_orgs = await self._repository.filter_by(owner_id=owner_id)
                if owned_orgs:
                    raise ConflictException(
                        error="User can only belong to one organization.",
                        errors={"code": "SINGLE_ORGANIZATION_LIMIT_EXCEEDED"},
                    )
                if self._member_repository is not None:
                    member_orgs = await self._member_repository.filter_by(
                        user_id=owner_id
                    )
                    if member_orgs:
                        raise ConflictException(
                            error="User can only belong to one organization.",
                            errors={"code": "SINGLE_ORGANIZATION_LIMIT_EXCEEDED"},
                        )

            normalized_name = name.strip().lower()
            slug = generate_slug(normalized_name)

            existing = await self._repository.get_by(name=normalized_name)
            if existing:
                raise ConflictException(
                    error=f"Organization with name '{normalized_name}' already exists.",
                )

            model_cls = cast("type[Any]", self._model)
            organization = model_cls(
                name=normalized_name,
                slug=slug,
                owner_id=owner_id,
                status=status,
                description=description,
                logo=logo,
            )
            created = await self._repository.add(organization)

            await event_bus.publish(
                OrganizationCreatedEvent(
                    organization_id=created.id,
                    organization_uuid=created.uuid,
                    name=created.name,
                    slug=created.slug,
                    owner_id=created.owner_id,
                )
            )

            return created
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to create organization.",
                internal_details=str(e),
            ) from e

    async def get_organization_by(self, **kwargs) -> TOrganization | None:
        """Retrieve an organization by filter criteria.

        Args:
            **kwargs: Filter keyword arguments.

        Returns:
            The matching organization instance or None.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.get_by(**kwargs)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve organization.",
                internal_details=str(e),
            ) from e

    async def update_organization(
        self,
        organization: TOrganization,
        name: str | None = None,
        description: str | None = None,
        logo: str | None = None,
        status: str | None = None,
    ) -> TOrganization:
        """Update an existing organization.

        Args:
            organization: The organization model instance to update.
            name: An optional new organization name (stored in lowercase).
            description: An optional new organization description.
            logo: An optional new organization logo.
            status: An optional new organization status.

        Returns:
            The updated organization instance.

        Raises:
            ConflictException: If a new name collides with an existing organization.
            DomainException: On unexpected failures.
        """
        try:
            if name is not None:
                normalized_name = name.strip().lower()
                existing = await self._repository.get_by(name=normalized_name)
                if existing and existing.id != organization.id:
                    raise ConflictException(
                        error=f"Organization with name '{normalized_name}' already exists.",
                    )
                organization.name = normalized_name
                organization.slug = generate_slug(normalized_name)
            if description is not None:
                organization.description = description
            if logo is not None:
                organization.logo = logo
            if status is not None:
                organization.status = status

            updated = await self._repository.update(organization)

            await event_bus.publish(
                OrganizationUpdatedEvent(
                    organization_id=updated.id,
                    organization_uuid=updated.uuid,
                    name=updated.name,
                    slug=updated.slug,
                    owner_id=updated.owner_id,
                )
            )

            return updated
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to update organization.",
                internal_details=str(e),
            ) from e

    async def list_organizations_by_owner(self, owner_id: int) -> list[TOrganization]:
        """List all organizations owned by the given user.

        Args:
            owner_id: The ID of the owner.

        Returns:
            A list of matching organization instances.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.filter_by(owner_id=owner_id)
        except Exception as e:
            raise DomainException(
                error="Failed to list organizations for owner.",
                internal_details=str(e),
            ) from e

    async def is_any_organization_setup(self) -> bool:
        """Check whether at least one organization exists in the database.

        Returns:
            True when at least one organization has been created.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._repository.get_first() is not None
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to check organization setup.",
                internal_details=str(e),
            ) from e

    async def get_organization_by_user_id(self, user_id: int) -> TOrganization | None:
        """Retrieve the organization the given user belongs to.

        Args:
            user_id: The ID of the user.

        Returns:
            The first organization the user is a member of, or None when the
            user has no membership.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            if self._member_repository is None:
                return None
            memberships = await self._member_repository.filter_by(user_id=user_id)
            if not memberships:
                return None
            return await self._repository.get_by(id=memberships[0].organization_id)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve organization by user.",
                internal_details=str(e),
            ) from e


def get_organization_service(
    session: AsyncSession,
    model: type[TOrganization],
    member_model: type | None = None,
    allow_multiple_organizations: bool = True,
) -> OrganizationService[TOrganization]:
    """Factory function to create an OrganizationService instance.

    Args:
        session: Async SQLAlchemy session.
        model: The OrganizationModel class.
        member_model: An optional OrganizationMemberModel class used to resolve
            organization memberships.
        allow_multiple_organizations: Whether users can belong to/own
            multiple organizations.

    Returns:
        A configured OrganizationService.
    """
    repository = OrganizationRepository(session=session, model=model)
    member_repository = (
        OrganizationMemberRepository(session=session, model=member_model)
        if member_model
        else None
    )
    return OrganizationService(
        repository=repository,
        model=model,
        member_repository=member_repository,
        allow_multiple_organizations=allow_multiple_organizations,
    )
