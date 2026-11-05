from .adapters import (
    OrganizationMembershipCheckImpl,
    get_organization_membership_check,
)
from .events import (
    OrganizationCreatedEvent,
    OrganizationDeletedEvent,
    OrganizationMemberAddedEvent,
    OrganizationMemberRemovedEvent,
    OrganizationMemberUpdatedEvent,
    OrganizationStatusChangedEvent,
    OrganizationUpdatedEvent,
)
from .models import (
    OrganizationMemberModelBase,
    OrganizationModel,
    OrganizationStatus,
    create_organization_member_model,
    create_organization_model,
    generate_slug,
)
from .organizations import Organizations
from .repositories import (
    OrganizationMemberRepository,
    OrganizationRepository,
)
from .schemas import (
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
from .services import (
    OrganizationMemberService,
    OrganizationService,
    OrganizationServiceRegistry,
    get_organization_member_service,
    get_organization_service,
)

__all__ = [
    "AdminOrganizationListResponseSchema",
    "AdminOrganizationResponseSchema",
    "OrganizationCreateSchema",
    "OrganizationCreatedEvent",
    "OrganizationDeletedEvent",
    "OrganizationListQuerySchema",
    "OrganizationListResponseSchema",
    "OrganizationMemberAddSchema",
    "OrganizationMemberAddedEvent",
    "OrganizationMemberModelBase",
    "OrganizationMemberRemovedEvent",
    "OrganizationMemberRepository",
    "OrganizationMemberResponseSchema",
    "OrganizationMemberService",
    "OrganizationMemberUpdateSchema",
    "OrganizationMemberUpdatedEvent",
    "OrganizationMembershipCheckImpl",
    "OrganizationModel",
    "OrganizationRepository",
    "OrganizationResponseSchema",
    "OrganizationService",
    "OrganizationServiceRegistry",
    "OrganizationStatsSchema",
    "OrganizationStatus",
    "OrganizationStatusChangedEvent",
    "OrganizationStatusUpdateSchema",
    "OrganizationUpdateSchema",
    "OrganizationUpdatedEvent",
    "Organizations",
    "create_organization_member_model",
    "create_organization_model",
    "generate_slug",
    "get_organization_member_service",
    "get_organization_membership_check",
    "get_organization_service",
]


def __getattr__(name: str):
    if name in __all__:
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
