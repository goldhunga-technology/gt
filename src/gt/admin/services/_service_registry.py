from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models import AdminModel
from gt.admin.services._admin_service import get_admin_service


class AdminServiceRegistry:
    """
    Per-session access to every admin service with the model pre-wired.

    Build one per request via ``admin.get_services(session)`` and access the
    service as an attribute, e.g. ``admin.get_services(session).admin``.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        admin_model: type[AdminModel],
    ):
        self._session = session
        self._admin_model = admin_model

    @cached_property
    def admin(self):
        """Service for administrator operations."""
        return get_admin_service(
            session=self._session,
            model=self._admin_model,
        )
