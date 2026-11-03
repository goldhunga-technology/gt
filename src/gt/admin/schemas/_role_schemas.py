from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gt.admin.models._role_model import generate_role_slug


class PermissionResponseSchema(BaseModel):
    """Public representation of a system permission."""

    name: str
    key: str
    description: str | None = None
    category: str
    is_system_permission: bool = True


class RoleCreateSchema(BaseModel):
    """Schema for creating a role."""

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    permissions: list[str] = Field(default_factory=list)
    is_system: bool = Field(default=False)
    status: str = Field(default="active", max_length=255)

    @model_validator(mode="after")
    def normalize(self):
        """Normalize the name and derive the slug when omitted."""
        self.name = self.name.strip()
        if not self.slug:
            self.slug = generate_role_slug(self.name)
        else:
            self.slug = generate_role_slug(self.slug)
        self.permissions = list(dict.fromkeys(self.permissions))
        return self

    model_config = ConfigDict(extra="forbid")


class RoleUpdateSchema(BaseModel):
    """Schema for updating a role."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    permissions: list[str] | None = Field(default=None)
    status: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def normalize(self):
        """Normalize the name and permissions when provided."""
        if self.name is not None:
            self.name = self.name.strip()
        if self.permissions is not None:
            self.permissions = list(dict.fromkeys(self.permissions))
        return self

    model_config = ConfigDict(extra="forbid")


class RoleListQuerySchema(BaseModel):
    """Query parameters for listing roles."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    search: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=255)
    is_system: bool | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")


class RoleResponseSchema(BaseModel):
    """Public representation of a role."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    slug: str
    description: str | None
    permissions: list[str]
    is_system: bool
    status: str
    created_at: datetime
    updated_at: datetime | None


class RoleListResponseSchema(BaseModel):
    """Paginated role list response."""

    items: list[RoleResponseSchema]
    total: int
    limit: int
    offset: int


class AdminRoleAssignSchema(BaseModel):
    """Schema for assigning a role to an administrator."""

    role_uuid: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")


class AdminRolesResponseSchema(BaseModel):
    """Roles assigned to an administrator, exposed as role slugs."""

    admin_uuid: str
    roles: list[str]
