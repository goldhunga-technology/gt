from datetime import datetime

from pydantic import ConfigDict, EmailStr, Field, model_validator
from pydantic.main import BaseModel

from gt.auth.schemas._auth_schemas import random_avatar_color


class AdminRegisterSchema(BaseModel):
    """Schema for administrator registration."""

    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    avatar_bg: str | None = Field(default_factory=random_avatar_color, max_length=255)

    @model_validator(mode="after")
    def calculate_full_name(self):
        """Derive the full name from the email when it is not provided."""
        if not self.full_name:
            username = self.email.split("@", 1)[0]
            self.full_name = (
                username.replace(".", " ").replace("_", " ").replace("-", " ").title()
            )
        return self


class AdminListQuerySchema(BaseModel):
    """Query parameters for listing administrators."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    search: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=255)


class AdminResponseSchema(BaseModel):
    """Public representation of an administrator.

    Password hashes are never exposed at the boundary.
    """

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    email: str
    full_name: str
    avatar_bg: str
    is_onboarded: bool
    status: str
    email_verified_at: datetime | None
    avatar: str | None


class AdminListResponseSchema(BaseModel):
    """Paginated administrator list response."""

    items: list[AdminResponseSchema]
    total: int
    limit: int
    offset: int
