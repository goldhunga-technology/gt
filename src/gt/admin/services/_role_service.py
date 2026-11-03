from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models._admin_model import AdminModel, TAdmin
from gt.admin.models._admin_role_model import AdminRoleModel, TAdminRole
from gt.admin.models._role_model import RoleModel, TRole, generate_role_slug
from gt.admin.repositories._admin_repository import AdminRepository
from gt.admin.repositories._admin_role_repository import AdminRoleRepository
from gt.admin.repositories._role_repository import RoleRepository
from gt.admin.seeders import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    DEFAULT_ROLES_PERMISSIONS,
    VALID_PERMISSION_KEYS,
)
from gt.exceptions import (
    ConflictException,
    DomainException,
    InvalidException,
    NotFoundException,
)


def _validate_permissions(permissions: list[str]) -> list[str]:
    """Validate and deduplicate permission keys against system permissions."""
    deduped = list(dict.fromkeys(permissions))
    invalid = [perm for perm in deduped if perm not in VALID_PERMISSION_KEYS]
    if invalid:
        raise InvalidException(
            error=f"Invalid permission keys: {', '.join(invalid)}.",
            errors={"permissions": f"Unknown permission keys: {', '.join(invalid)}."},
        )
    return deduped


class RoleService[
    TRole: RoleModel,
    TAdminRole: AdminRoleModel,
    TAdmin: AdminModel,
]:
    """Service for managing role and role-assignment operations."""

    def __init__(
        self,
        role_repository: RoleRepository[TRole],
        admin_role_repository: AdminRoleRepository[TAdminRole, TRole],
        admin_repository: AdminRepository[TAdmin],
        role_model: type[TRole],
        admin_role_model: type[TAdminRole],
    ):
        """Initialize the service with repositories and models.

        Args:
            role_repository: The RoleRepository instance.
            admin_role_repository: The AdminRoleRepository instance.
            admin_repository: The AdminRepository instance.
            role_model: The RoleModel class.
            admin_role_model: The AdminRoleModel class.
        """
        self._role_repository = role_repository
        self._admin_role_repository = admin_role_repository
        self._admin_repository = admin_repository
        self._role_model = role_model
        self._admin_role_model = admin_role_model

    def list_permissions(self) -> list[dict[str, Any]]:
        """Return the catalog of available system permissions."""
        return [dict(item) for item in DEFAULT_PERMISSIONS]

    async def seed_default_roles(self) -> dict[str, TRole]:
        """Idempotently seed all default roles and their permissions.

        Returns:
            Mapping of role slug to the persisted role instance.
        """
        try:
            roles_by_slug: dict[str, TRole] = {}
            for spec in DEFAULT_ROLES:
                slug = generate_role_slug(spec.get("slug") or spec["name"])
                existing = await self._role_repository.get_by(slug=slug)
                if existing:
                    roles_by_slug[slug] = existing
                    continue

                permissions = DEFAULT_ROLES_PERMISSIONS.get(
                    slug,
                    DEFAULT_ROLES_PERMISSIONS.get(spec["name"], []),
                )
                role = await self.create_role(
                    name=spec["name"],
                    slug=slug,
                    description=spec.get("description"),
                    permissions=permissions,
                    is_system=bool(spec.get("is_system", True)),
                    status="active",
                )
                roles_by_slug[slug] = role
            return roles_by_slug
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to seed default roles.",
                internal_details=str(e),
            ) from e

    async def seed_default_roles_and_assign_role(
        self,
        *,
        admin_id: int,
        role_slug: str = "superadmin",
        assigned_by: int | None = None,
    ) -> TAdminRole:
        """Seed all default roles and assign the specified role (default: superadmin) to an admin.

        Runs against the caller's session so it composes into the admin creation flow.

        Args:
            admin_id: The internal administrator id.
            role_slug: The slug of the role to assign (defaults to 'superadmin').
            assigned_by: Optional internal id of the assigning administrator.

        Returns:
            The persisted role assignment instance.
        """
        try:
            roles_by_slug = await self.seed_default_roles()
            normalized_slug = generate_role_slug(role_slug)
            role = roles_by_slug.get(normalized_slug)
            if not role:
                role = await self._role_repository.get_by(slug=normalized_slug)
            if not role:
                raise NotFoundException(
                    error=f"Role '{normalized_slug}' not found after seeding.",
                    errors={
                        "role_slug": f"No role exists with slug '{normalized_slug}'."
                    },
                )

            existing = await self._admin_role_repository.get_by(
                admin_id=admin_id, role_id=role.id
            )
            if existing:
                return existing

            model_cls = cast("type[Any]", self._admin_role_model)
            assignment = model_cls(
                admin_id=admin_id,
                role_id=role.id,
                assigned_by=assigned_by,
            )
            return await self._admin_role_repository.add(assignment)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to seed default roles and assign role to admin.",
                internal_details=str(e),
            ) from e

    async def create_role(
        self,
        *,
        name: str,
        slug: str | None = None,
        description: str | None = None,
        permissions: list[str] | None = None,
        is_system: bool = False,
        status: str = "active",
    ) -> TRole:
        """Create a new role.

        Args:
            name: The role display name.
            slug: Optional machine key; derived from the name when omitted.
            description: Optional role description.
            permissions: Optional permission identifiers.
            is_system: Whether the role is a built-in system role.
            status: The role status.

        Returns:
            The created role instance.

        Raises:
            InvalidException: If the name, slug, or permissions are invalid.
            ConflictException: If a role with the same name or slug exists.
            DomainException: On unexpected failures.
        """
        try:
            normalized_name = name.strip()
            if not normalized_name:
                raise InvalidException(
                    error="Role name cannot be empty.",
                    errors={"name": "Role name cannot be empty."},
                )

            role_slug = generate_role_slug(slug or normalized_name)
            if not role_slug:
                raise InvalidException(
                    error="Role slug cannot be empty.",
                    errors={"slug": "Role slug cannot be empty."},
                )

            validated_permissions = _validate_permissions(permissions or [])

            if await self._role_repository.get_by(name=normalized_name):
                raise ConflictException(
                    error=f"Role with name '{normalized_name}' already exists.",
                    errors={"name": "This role name is already in use."},
                )

            if await self._role_repository.get_by(slug=role_slug):
                raise ConflictException(
                    error=f"Role with slug '{role_slug}' already exists.",
                    errors={"slug": "This role slug is already in use."},
                )

            model_cls = cast("type[Any]", self._role_model)
            role = model_cls(
                name=normalized_name,
                slug=role_slug,
                description=description,
                permissions=validated_permissions,
                is_system=is_system,
                status=status,
            )
            return await self._role_repository.add(role)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to create role.",
                internal_details=str(e),
            ) from e

    async def get_role_by(self, **kwargs) -> TRole | None:
        """Retrieve a role by filter criteria.

        Args:
            **kwargs: Filter keyword arguments.

        Returns:
            The matching role instance or None.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._role_repository.get_by(**kwargs)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve role.",
                internal_details=str(e),
            ) from e

    async def get_role_or_raise(self, role_uuid: str) -> TRole:
        """Retrieve a role by UUID or raise when missing.

        Args:
            role_uuid: The public role UUID.

        Returns:
            The matching role instance.

        Raises:
            NotFoundException: If the role does not exist.
        """
        role = await self.get_role_by(uuid=role_uuid)
        if not role:
            raise NotFoundException(
                error="Role not found.",
                errors={"role_uuid": "No role exists with this UUID."},
            )
        return role

    async def list_roles(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        is_system: bool | None = None,
    ) -> tuple[list[TRole], int]:
        """List roles with pagination and optional filters.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            search: Optional case-insensitive name/slug search term.
            status: Optional status filter.
            is_system: Optional system-role filter.

        Returns:
            A tuple of roles and the total number of matches.

        Raises:
            DomainException: On unexpected failures.
        """
        try:
            return await self._role_repository.paginate(
                limit=limit,
                offset=offset,
                search=search,
                status=status,
                is_system=is_system,
            )
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to list roles.",
                internal_details=str(e),
            ) from e

    async def update_role(
        self,
        *,
        role_uuid: str,
        name: str | None = None,
        description: str | None = None,
        permissions: list[str] | None = None,
        status: str | None = None,
    ) -> TRole:
        """Update an existing role.

        Args:
            role_uuid: The public role UUID.
            name: Optional new display name.
            description: Optional new description.
            permissions: Optional replacement permission list.
            status: Optional new status.

        Returns:
            The updated role instance.

        Raises:
            NotFoundException: If the role does not exist.
            ConflictException: If the new name is already in use or a protected
                system role's name/permissions/status are modified.
            DomainException: On unexpected failures.
        """
        try:
            role = await self.get_role_or_raise(role_uuid)

            if role.is_system:
                if name is not None and name.strip() != role.name:
                    raise ConflictException(
                        error="System role name cannot be modified.",
                        errors={"name": "This role is a protected system role."},
                    )
                if (
                    permissions is not None
                    and _validate_permissions(permissions) != role.permissions
                ):
                    raise ConflictException(
                        error="System role permissions cannot be modified.",
                        errors={"permissions": "This role is a protected system role."},
                    )
                if status is not None and status != "active":
                    raise ConflictException(
                        error="System roles cannot be deactivated.",
                        errors={"status": "This role is a protected system role."},
                    )

            if name is not None:
                normalized_name = name.strip()
                if not normalized_name:
                    raise InvalidException(
                        error="Role name cannot be empty.",
                        errors={"name": "Role name cannot be empty."},
                    )
                if normalized_name != role.name:
                    existing = await self._role_repository.get_by(name=normalized_name)
                    if existing and existing.id != role.id:
                        raise ConflictException(
                            error=f"Role with name '{normalized_name}' already exists.",
                            errors={"name": "This role name is already in use."},
                        )
                    role.name = normalized_name

            if description is not None:
                role.description = description
            if permissions is not None:
                role.permissions = _validate_permissions(permissions)
            if status is not None:
                role.status = status

            role.touch()
            return await self._role_repository.update(role)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to update role.",
                internal_details=str(e),
            ) from e

    async def delete_role(self, role_uuid: str) -> None:
        """Delete a role.

        Args:
            role_uuid: The public role UUID.

        Raises:
            NotFoundException: If the role does not exist.
            ConflictException: If the role is a protected system role.
            DomainException: On unexpected failures.
        """
        try:
            role = await self.get_role_or_raise(role_uuid)
            if role.is_system:
                raise ConflictException(
                    error="System roles cannot be deleted.",
                    errors={"role_uuid": "This role is a protected system role."},
                )
            await self._role_repository.delete(role)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to delete role.",
                internal_details=str(e),
            ) from e

    async def assign_role_to_admin(
        self,
        *,
        admin_uuid: str,
        role_uuid: str,
        assigned_by: int | None = None,
    ) -> TAdminRole:
        """Assign a role to an administrator.

        Args:
            admin_uuid: The public administrator UUID.
            role_uuid: The public role UUID.
            assigned_by: Optional internal id of the assigning administrator.

        Returns:
            The created assignment instance.

        Raises:
            NotFoundException: If the administrator or role does not exist.
            InvalidException: If the role is inactive.
            ConflictException: If the role is already assigned.
            DomainException: On unexpected failures.
        """
        try:
            admin = await self._admin_repository.get_by(uuid=admin_uuid)
            if not admin:
                raise NotFoundException(
                    error="Admin not found.",
                    errors={"admin_uuid": "No admin exists with this UUID."},
                )

            role = await self.get_role_or_raise(role_uuid)
            if not role.is_active():
                raise InvalidException(
                    error="Role is inactive.",
                    errors={"role_uuid": "Inactive roles cannot be assigned."},
                )

            existing = await self._admin_role_repository.get_by(
                admin_id=admin.id, role_id=role.id
            )
            if existing:
                raise ConflictException(
                    error="Role is already assigned to this admin.",
                    errors={"role_uuid": "This role is already assigned."},
                )

            model_cls = cast("type[Any]", self._admin_role_model)
            assignment = model_cls(
                admin_id=admin.id,
                role_id=role.id,
                assigned_by=assigned_by,
            )
            return await self._admin_role_repository.add(assignment)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to assign role to admin.",
                internal_details=str(e),
            ) from e

    async def revoke_role_from_admin(
        self,
        *,
        admin_uuid: str,
        role_uuid: str,
    ) -> None:
        """Revoke a role from an administrator.

        Args:
            admin_uuid: The public administrator UUID.
            role_uuid: The public role UUID.

        Raises:
            NotFoundException: If the admin, role or assignment does not exist.
            ConflictException: If revoking superadmin from the last remaining superadmin.
            DomainException: On unexpected failures.
        """
        try:
            admin = await self._admin_repository.get_by(uuid=admin_uuid)
            if not admin:
                raise NotFoundException(
                    error="Admin not found.",
                    errors={"admin_uuid": "No admin exists with this UUID."},
                )

            role = await self.get_role_or_raise(role_uuid)
            assignment = await self._admin_role_repository.get_by(
                admin_id=admin.id, role_id=role.id
            )
            if not assignment:
                raise NotFoundException(
                    error="Role is not assigned to this admin.",
                    errors={"role_uuid": "This role is not assigned."},
                )

            if role.slug == "superadmin" or "*" in role.permissions:
                remaining_count = await self._admin_role_repository.count_by_role_id(
                    role.id
                )
                if remaining_count <= 1:
                    raise ConflictException(
                        error="Cannot revoke superadmin role from the last superadmin.",
                        errors={
                            "role_uuid": "At least one administrator must retain the superadmin role."
                        },
                    )

            await self._admin_role_repository.delete(assignment)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to revoke role from admin.",
                internal_details=str(e),
            ) from e

    async def get_admin_roles(self, admin_uuid: str) -> tuple[TAdmin, list[TRole]]:
        """Retrieve an administrator and their assigned roles.

        Args:
            admin_uuid: The public administrator UUID.

        Returns:
            A tuple of the administrator and their roles.

        Raises:
            NotFoundException: If the administrator does not exist.
            DomainException: On unexpected failures.
        """
        try:
            admin = await self._admin_repository.get_by(uuid=admin_uuid)
            if not admin:
                raise NotFoundException(
                    error="Admin not found.",
                    errors={"admin_uuid": "No admin exists with this UUID."},
                )
            roles = await self._admin_role_repository.get_roles_for_admin(admin.id)
            return admin, roles
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve admin roles.",
                internal_details=str(e),
            ) from e

    async def get_role_slugs_for_admins(
        self, admin_ids: list[int]
    ) -> dict[int, list[str]]:
        """Resolve role slugs for several administrators in one query.

        Args:
            admin_ids: The internal administrator ids.

        Returns:
            A mapping of administrator id to their role slugs.
        """
        try:
            roles_by_admin = await self._admin_role_repository.get_roles_for_admins(
                admin_ids
            )
            return {
                admin_id: [role.slug for role in roles]
                for admin_id, roles in roles_by_admin.items()
            }
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve admin role slugs.",
                internal_details=str(e),
            ) from e

    async def get_permissions_for_admin(self, admin_id: int) -> list[str]:
        """Retrieve the deduplicated list of active permissions granted to an administrator.

        Args:
            admin_id: The internal administrator id.

        Returns:
            A list of permission keys granted by active roles.
        """
        roles = await self._admin_role_repository.get_roles_for_admin(admin_id)
        permissions: list[str] = []
        for role in roles:
            if role.is_active():
                permissions.extend(role.permissions)
        return list(dict.fromkeys(permissions))

    async def admin_has_role(self, admin_id: int, role_slug: str) -> bool:
        """Check whether an administrator holds an active role (or superadmin wildcard).

        Args:
            admin_id: The internal administrator id.
            role_slug: The role slug to check.

        Returns:
            bool: True when the role (or superadmin wildcard) is assigned and active.
        """
        roles = await self._admin_role_repository.get_roles_for_admin(admin_id)
        return any(
            role.is_active() and (role.slug == role_slug or "*" in role.permissions)
            for role in roles
        )

    async def admin_has_permission(self, admin_id: int, permission: str) -> bool:
        """Check whether an administrator is granted a permission.

        Inactive roles are ignored.

        Args:
            admin_id: The internal administrator id.
            permission: The permission identifier to check.

        Returns:
            bool: True when any active role grants the permission.
        """
        roles = await self._admin_role_repository.get_roles_for_admin(admin_id)
        return any(
            role.is_active() and role.has_permission(permission) for role in roles
        )


def get_role_service(
    *,
    session: AsyncSession,
    role_model: type[TRole],
    admin_role_model: type[TAdminRole],
    admin_model: type[TAdmin],
) -> RoleService[TRole, TAdminRole, TAdmin]:
    """Factory function to create a RoleService instance.

    Args:
        session: Async SQLAlchemy session.
        role_model: The RoleModel class.
        admin_role_model: The AdminRoleModel class.
        admin_model: The AdminModel class.

    Returns:
        A configured RoleService.
    """
    role_repository = RoleRepository(session=session, model=role_model)
    admin_role_repository = AdminRoleRepository(
        session=session, model=admin_role_model, role_model=role_model
    )
    admin_repository = AdminRepository(session=session, model=admin_model)
    return RoleService(
        role_repository=role_repository,
        admin_role_repository=admin_role_repository,
        admin_repository=admin_repository,
        role_model=role_model,
        admin_role_model=admin_role_model,
    )
