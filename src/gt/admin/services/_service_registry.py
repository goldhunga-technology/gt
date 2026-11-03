from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models import AdminModel
from gt.admin.models._admin_role_model import AdminRoleModel
from gt.admin.models._admin_session_model import AdminSessionModelBase
from gt.admin.models._role_model import RoleModel
from gt.admin.policies import AdminPolicy
from gt.admin.services._admin_login_service import get_admin_login_service
from gt.admin.services._admin_service import get_admin_service
from gt.admin.services._admin_session_service import get_admin_session_service
from gt.admin.services._role_service import get_role_service


class AdminServiceRegistry:
    """
    Per-session access to every admin service with the models pre-wired.

    Build one per request via ``admin.get_services(session)`` and access the
    service as an attribute, e.g. ``admin.get_services(session).admin``.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        admin_model: type[AdminModel],
        admin_session_model: type[AdminSessionModelBase],
        role_model: type[RoleModel] | None = None,
        admin_role_model: type[AdminRoleModel] | None = None,
        admin_policy: AdminPolicy | None = None,
    ):
        self._session = session
        self._admin_model = admin_model
        self._admin_session_model = admin_session_model
        self._role_model = role_model
        self._admin_role_model = admin_role_model
        self._admin_policy = admin_policy

    @cached_property
    def admin(self):
        """Service for administrator operations."""
        return get_admin_service(
            session=self._session,
            model=self._admin_model,
            role_service=self.role,
        )

    @cached_property
    def login(self):
        """Service for administrator login and logout flows."""
        return get_admin_login_service(
            session=self._session,
            admin_model=self._admin_model,
            admin_session_model=self._admin_session_model,
        )

    @cached_property
    def session(self):
        """Service for administrator session operations."""
        return get_admin_session_service(
            session=self._session,
            model=self._admin_session_model,
        )

    @cached_property
    def role(self):
        """Service for administrator role operations."""
        if self._role_model is None or self._admin_role_model is None:
            return None
        return get_role_service(
            session=self._session,
            role_model=self._role_model,
            admin_role_model=self._admin_role_model,
            admin_model=self._admin_model,
        )
