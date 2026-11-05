from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gt.organizations.models._organization_model import OrganizationStatus


class OrganizationCreateSchema(BaseModel):
    """Schema for creating an organization."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    logo: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def normalize_name(self):
        """Normalize the name to lowercase and derive the slug from it."""
        self.name = self.name.strip().lower()
        return self

    model_config = ConfigDict(extra="forbid")


class OrganizationUpdateSchema(BaseModel):
    """Schema for updating an organization."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    logo: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def normalize_name(self):
        """Normalize the name to lowercase if provided."""
        if self.name is not None:
            self.name = self.name.strip().lower()
        return self

    model_config = ConfigDict(extra="forbid")


class OrganizationStatusUpdateSchema(BaseModel):
    """Schema for changing an organization's status."""

    status: OrganizationStatus
    reason: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class OrganizationListQuerySchema(BaseModel):
    """Query parameters for listing organizations."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    search: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class OrganizationResponseSchema(BaseModel):
    """Schema for an organization response."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    slug: str
    owner_id: int
    status: str
    description: str | None
    logo: str | None
    trial_ends_at: datetime | None = None
    status_changed_at: datetime | None = None
    status_changed_by: int | None = None
    status_reason: str | None = None


class OrganizationListResponseSchema(BaseModel):
    """Paginated organization list response."""

    items: list[OrganizationResponseSchema]
    total: int
    limit: int
    offset: int


class OrganizationStatsSchema(BaseModel):
    """Aggregate organization counts."""

    total: int
    active: int
    trial: int
    inactive: int
    cancelled: int


class AdminOrganizationResponseSchema(OrganizationResponseSchema):
    """Organization representation enriched with administrator-only details."""

    member_count: int = 0


class AdminOrganizationListResponseSchema(BaseModel):
    """Paginated administrator organization list response with statistics."""

    items: list[AdminOrganizationResponseSchema]
    total: int
    limit: int
    offset: int
    stats: OrganizationStatsSchema


class OrganizationMemberAddSchema(BaseModel):
    """Schema for adding a member to an organization.

    The externally facing identifier is the user's public ``uuid``.
    Internally the boundary resolves it to the integer ``id`` used by the
    services for fast indexed lookups.
    """

    user_uuid: UUID = Field(..., description="Public UUID of the user to add.")
    status: str = Field(default="active", max_length=255)
    role: str = Field(default="member", max_length=255)


class OrganizationMemberUpdateSchema(BaseModel):
    """Schema for updating an organization member."""

    status: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=255)


class OrganizationMemberResponseSchema(BaseModel):
    """Schema for an organization member response.

    Only public uuids leave the application; integer primary keys stay
    internal.
    """

    uuid: str
    user_uuid: str | None = None
    organization_uuid: str | None = None
    status: str
    role: str
