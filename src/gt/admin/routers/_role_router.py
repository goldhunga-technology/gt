from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_201_CREATED

from gt.admin.schemas._role_schemas import (
    AdminRoleAssignSchema,
    AdminRolesResponseSchema,
    PermissionResponseSchema,
    RoleCreateSchema,
    RoleListResponseSchema,
    RoleResponseSchema,
    RoleUpdateSchema,
)
from gt.admin.uow import AdminUOW
from gt.exceptions import ServerException
from gt.response import cr


def _admin_auth_not_configured():
    """Dependency used when the host has not supplied a current_admin resolver."""
    raise ServerException(
        error="Admin authentication is not configured.",
        errors={"code": "ADMIN_AUTH_NOT_CONFIGURED"},
    )


def _resolve_current_admin_dependency(admin):
    """Resolve the configured current-admin dependency for the role routes."""
    current_admin_dependency = getattr(admin, "current_admin", None)
    if current_admin_dependency is None:
        build_dependency = getattr(admin, "build_current_admin_dependency", None)
        current_admin_dependency = (
            build_dependency() if build_dependency else _admin_auth_not_configured
        )
    return current_admin_dependency


def create_role_router(*, admin):
    """Create a router for administrator role operations."""
    session_factory = admin.session_factory
    current_admin_dependency = _resolve_current_admin_dependency(admin)

    router = APIRouter()

    @router.get("/permissions")
    async def list_permissions(
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """List all available system permissions."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role
            permissions = role_service.list_permissions()
            payload = [
                PermissionResponseSchema.model_validate(perm).model_dump()
                for perm in permissions
            ]

        return cr.success(
            data=payload,
            message="Permissions retrieved successfully.",
        )

    @router.post("/roles", status_code=HTTP_201_CREATED)
    async def create_role(
        body: RoleCreateSchema,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """Create a new role."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role

            async with AdminUOW(session):
                role = await role_service.create_role(
                    name=body.name,
                    slug=body.slug,
                    description=body.description,
                    permissions=body.permissions,
                    is_system=body.is_system,
                    status=body.status,
                )
                payload = RoleResponseSchema.model_validate(role).model_dump()

        return cr.success(
            data=payload,
            message="Role created successfully.",
            status_code=HTTP_201_CREATED,
        )

    @router.get("/roles")
    async def list_roles(
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        search: Annotated[str | None, Query(max_length=255)] = None,
        status: Annotated[str | None, Query(max_length=255)] = None,
        is_system: Annotated[bool | None, Query()] = None,
    ):
        """List roles with pagination and optional filters."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role
            roles, total = await role_service.list_roles(
                limit=limit,
                offset=offset,
                search=search,
                status=status,
                is_system=is_system,
            )
            payload = RoleListResponseSchema(
                items=[RoleResponseSchema.model_validate(role) for role in roles],
                total=total,
                limit=limit,
                offset=offset,
            ).model_dump()

        return cr.success(
            data=payload,
            message="Roles retrieved successfully.",
        )

    @router.get("/roles/{role_uuid}")
    async def get_role(
        role_uuid: str,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """Retrieve a single role by its public UUID."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role
            role = await role_service.get_role_or_raise(role_uuid)
            payload = RoleResponseSchema.model_validate(role).model_dump()

        return cr.success(
            data=payload,
            message="Role retrieved successfully.",
        )

    @router.patch("/roles/{role_uuid}")
    async def update_role(
        role_uuid: str,
        body: RoleUpdateSchema,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """Update a role."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role

            async with AdminUOW(session):
                role = await role_service.update_role(
                    role_uuid=role_uuid,
                    name=body.name,
                    description=body.description,
                    permissions=body.permissions,
                    status=body.status,
                )
                payload = RoleResponseSchema.model_validate(role).model_dump()

        return cr.success(
            data=payload,
            message="Role updated successfully.",
        )

    @router.delete("/roles/{role_uuid}")
    async def delete_role(
        role_uuid: str,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """Delete a role."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role

            async with AdminUOW(session):
                await role_service.delete_role(role_uuid)

        return cr.success(message="Role deleted successfully.")

    @router.get("/admins/{admin_uuid}/roles")
    async def list_admin_roles(
        admin_uuid: str,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """List the roles assigned to an administrator."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role
            admin_record, roles = await role_service.get_admin_roles(admin_uuid)
            payload = AdminRolesResponseSchema(
                admin_uuid=admin_record.uuid,
                roles=[role.slug for role in roles],
            ).model_dump()

        return cr.success(
            data=payload,
            message="Admin roles retrieved successfully.",
        )

    @router.post("/admins/{admin_uuid}/roles", status_code=HTTP_201_CREATED)
    async def assign_admin_role(
        admin_uuid: str,
        body: AdminRoleAssignSchema,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """Assign a role to an administrator."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role

            async with AdminUOW(session):
                await role_service.assign_role_to_admin(
                    admin_uuid=admin_uuid,
                    role_uuid=body.role_uuid,
                    assigned_by=_current_admin.id,
                )
                admin_record, roles = await role_service.get_admin_roles(admin_uuid)
                payload = AdminRolesResponseSchema(
                    admin_uuid=admin_record.uuid,
                    roles=[role.slug for role in roles],
                ).model_dump()

        return cr.success(
            data=payload,
            message="Role assigned successfully.",
            status_code=HTTP_201_CREATED,
        )

    @router.delete("/admins/{admin_uuid}/roles/{role_uuid}")
    async def revoke_admin_role(
        admin_uuid: str,
        role_uuid: str,
        _current_admin: Annotated[Any, Depends(current_admin_dependency)],
    ):
        """Revoke a role from an administrator."""
        async with session_factory() as session:
            role_service = admin.get_services(session).role

            async with AdminUOW(session):
                await role_service.revoke_role_from_admin(
                    admin_uuid=admin_uuid,
                    role_uuid=role_uuid,
                )
                admin_record, roles = await role_service.get_admin_roles(admin_uuid)
                payload = AdminRolesResponseSchema(
                    admin_uuid=admin_record.uuid,
                    roles=[role.slug for role in roles],
                ).model_dump()

        return cr.success(
            data=payload,
            message="Role revoked successfully.",
        )

    return router
