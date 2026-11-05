from ._organization_schemas import (
    AdminOrganizationListResponseSchema,
    AdminOrganizationResponseSchema,
    OrganizationCreateSchema,
    OrganizationListQuerySchema,
    OrganizationListResponseSchema,
    OrganizationMemberAddSchema,
    OrganizationMemberResponseSchema,
    OrganizationMemberUpdateSchema,
    OrganizationResponseSchema,
    OrganizationStatsSchema,
    OrganizationStatusUpdateSchema,
    OrganizationUpdateSchema,
)

__all__ = [
    "AdminOrganizationListResponseSchema",
    "AdminOrganizationResponseSchema",
    "OrganizationCreateSchema",
    "OrganizationListQuerySchema",
    "OrganizationListResponseSchema",
    "OrganizationMemberAddSchema",
    "OrganizationMemberResponseSchema",
    "OrganizationMemberUpdateSchema",
    "OrganizationResponseSchema",
    "OrganizationStatsSchema",
    "OrganizationStatusUpdateSchema",
    "OrganizationUpdateSchema",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
