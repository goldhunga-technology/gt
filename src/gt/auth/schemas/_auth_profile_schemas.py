from pydantic import Field
from pydantic.main import BaseModel


class AuthProfileUpdateSchema(BaseModel):
    """
    Schema for updating a user's profile.
    """

    full_name: str | None = Field(None, max_length=255)
    avatar_bg: str | None = Field(None, max_length=255)
    avatar: str | None = Field(None, max_length=255)
    language: str | None = Field(None, max_length=10)


class AuthChangeLanguageSchema(BaseModel):
    """
    Schema for changing a user's language preference.
    """

    language: str = Field(..., min_length=2, max_length=10)


class AuthDeactivateSchema(BaseModel):
    """
    Schema for deactivating a user account.
    """

    password: str = Field(..., max_length=128)
