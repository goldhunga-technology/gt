from sqlalchemy.ext.asyncio import AsyncSession

from gt.admin.models import AdminModel, TAdmin
from gt.admin.models._admin_session_model import (
    AdminSessionModelBase,
    TAdminSession,
)
from gt.admin.repositories import AdminRepository
from gt.admin.services._admin_session_service import (
    AdminSessionService,
    get_admin_session_service,
)
from gt.auth.services.hash._hash_service import HasherService
from gt.exceptions import DomainException
from gt.exceptions._base_exceptions import InvalidException


class AdminLoginService[
    TAdmin: AdminModel,
    TAdminSession: AdminSessionModelBase,
]:
    """Service for handling administrator login functionality."""

    def __init__(
        self,
        admin_repository: AdminRepository[TAdmin],
        admin_model: type[TAdmin],
        session_service: AdminSessionService[TAdminSession],
        hash_service: HasherService,
    ):
        self._admin_repository = admin_repository
        self._admin_model = admin_model
        self._session_service = session_service
        self._hash_service = hash_service

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str,
        device: str,
        browser: str,
        session_expire_minutes: int,
    ) -> tuple[TAdmin, TAdminSession]:
        """Authenticate an administrator with the provided email and password."""
        try:
            admin = await self._admin_repository.get_by(email=email.lower())
            if not admin:
                self._hash_service.dummy_verify(password)
                raise InvalidException(
                    error="Invalid email or password.",
                    errors={"email": "Invalid email or password."},
                )

            if not admin.hashed_password:
                self._hash_service.dummy_verify(password)
                raise InvalidException(
                    error="Invalid email or password.",
                    errors={"email": "Invalid email or password."},
                )

            if not self._hash_service.verify(admin.hashed_password, password):
                raise InvalidException(
                    error="Invalid email or password.",
                    errors={"email": "Invalid email or password."},
                )

            if not admin.is_active():
                raise InvalidException(
                    error="Admin account is inactive.",
                    errors={"code": "ADMIN_INACTIVE"},
                )

            session = await self._session_service.create_session(
                admin_id=admin.id,
                expire_minutes=session_expire_minutes,
                device=device,
                ip_address=ip_address,
                browser=browser,
            )

            return admin, session
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to login.",
                internal_details=str(e),
            ) from e

    async def logout(self, session_uuid: str) -> None:
        """Logout an administrator by invalidating their session."""
        try:
            await self._session_service.invalidate_session(session_uuid=session_uuid)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to logout.",
                internal_details=str(e),
            ) from e


def get_admin_login_service(
    *,
    session: AsyncSession,
    admin_model: type[TAdmin],
    admin_session_model: type[TAdminSession],
) -> AdminLoginService[TAdmin, TAdminSession]:
    """Factory function to create an AdminLoginService instance."""
    repository = AdminRepository(session=session, model=admin_model)
    session_service = get_admin_session_service(
        session=session, model=admin_session_model
    )
    hash_service = HasherService()
    return AdminLoginService(
        admin_repository=repository,
        admin_model=admin_model,
        session_service=session_service,
        hash_service=hash_service,
    )
