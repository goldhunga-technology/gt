from ._organization_member_model import (
    OrganizationMemberModelBase,
    TOrganizationMember,
    create_organization_member_model,
)
from ._organization_model import (
    OrganizationModel,
    OrganizationStatus,
    TOrganization,
    create_organization_model,
    generate_slug,
)

__all__ = [
    "OrganizationMemberModelBase",
    "OrganizationModel",
    "OrganizationStatus",
    "TOrganization",
    "TOrganizationMember",
    "create_organization_member_model",
    "create_organization_model",
    "generate_slug",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
