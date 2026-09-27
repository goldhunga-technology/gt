from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.models._auth_user_model import TUser
from gt.auth.models._auth_user_session_model import AuthUserSessionModelBase
from gt.auth.models._auth_user_tokens_model import AuthUserTokensModelBase
from gt.auth.repositories._auth_user_session_repository import TSession
from gt.auth.repositories._auth_user_tokens_repository import TToken
from gt.auth.services._auth_user_session_service import (
    AuthUserSessionService,
    get_auth_user_session_service,
)
from gt.auth.services._auth_user_tokens_service import (
    AuthUserTokensService,
    get_auth_user_tokens_service,
)
from gt.exceptions import ConflictException, DomainException
from gt.exceptions._base_exceptions import InvalidException

from ..events import (
    UserCreatedEvent,
    UserDeactivatedEvent,
    UserProfileUpdatedEvent,
    event_bus,
)
from ..models import AuthUserModel
from ..repositories import AuthUserRepository
from ..repositories._auth_user_account_repository import TAccount
from ..services import AuthUserAccountService
from ..services._auth_user_account_service import (
    ACCOUNT_TYPE_LITERAL,
    get_auth_user_account_service,
)


class AuthUserService[
    TUser: AuthUserModel,
    TSession: AuthUserSessionModelBase,
    TToken: AuthUserTokensModelBase,
]:
    """
    Service class for handling authentication-related operations for users.
    """

    def __init__(
        self,
        repository: AuthUserRepository,
        model: type[TUser],
        account_service: AuthUserAccountService,
        session_service: AuthUserSessionService[TSession],
        token_service: AuthUserTokensService[TToken],
    ):
        """
        Initialize the AuthUserService with a user repository.
        """

        self._repository = repository
        self._model = model
        self._account_service = account_service
        self._session_service = session_service
        self._token_service = token_service

    async def create_user(
        self,
        user: TUser,
        ip_address: str,
        device: str,
        browser: str,
        session_expire_minutes: int,
        email_token_expiry_minutes: int,
        email_token_digit: int,
        password: str | None = None,
    ) -> tuple[TUser, TSession]:
        """
        Create a new user instance.
        """
        try:
            check_existing_user = await self._repository.get_by(email=user.email)
            if check_existing_user:
                raise ConflictException(
                    error=f"User with email {user.email} already exists.",
                    errors={"email": "This email is already registered."},
                )
            new_user = await self._repository.add(user)

            await self._add_user_account(
                user_id=new_user.id, type="credentials", password=password
            )

            session = await self._create_user_session(
                user_id=new_user.id,
                expire_minutes=session_expire_minutes,
                device=device,
                ip_address=ip_address,
                browser=browser,
            )

            _, plain_token = await self.get_email_verification_token(
                user_id=new_user.id,
                email_token_expiry_minutes=email_token_expiry_minutes,
                email_token_digit=email_token_digit,
            )

            await event_bus.publish(
                UserCreatedEvent(
                    user_id=new_user.id,
                    user_uuid=new_user.uuid,
                    full_name=new_user.full_name,
                    email=new_user.email,
                    email_token=plain_token,
                    email_token_expiry_minutes=email_token_expiry_minutes,
                )
            )
            return new_user, session
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to create user.",
                internal_details=str(e),
            ) from e

    async def _add_user_account(
        self,
        user_id: int,
        type: ACCOUNT_TYPE_LITERAL,
        password: str | None = None,
        provider: str | None = None,
    ) -> None:
        """
        Add a user account for the specified user.
        """
        try:
            await self._account_service.create_account(
                user_id=user_id, type=type, password=password, provider=provider
            )
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to add user account.",
                internal_details=str(e),
            ) from e

    async def update_user(self, user: TUser) -> TUser:
        """
        Update an existing user instance.
        """
        try:
            updated_user = await self._repository.update(user)
            return updated_user
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to update user.",
                internal_details=str(e),
            ) from e

    async def update_profile(
        self,
        user: TUser,
        full_name: str | None = None,
        avatar_bg: str | None = None,
        avatar: str | None = None,
    ) -> TUser:
        """
        Update a user's profile fields and publish a profile updated event.
        """
        try:
            if full_name is not None:
                user.full_name = full_name
            if avatar_bg is not None:
                user.avatar_bg = avatar_bg
            if avatar is not None:
                user.avatar = avatar

            updated_user = await self.update_user(user)

            await event_bus.publish(
                UserProfileUpdatedEvent(
                    user_id=updated_user.id,
                    full_name=updated_user.full_name,
                    email=updated_user.email,
                    user_uuid=updated_user.uuid,
                    avatar=updated_user.avatar,
                    avatar_bg=updated_user.avatar_bg,
                )
            )
            return updated_user
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to update profile.",
                internal_details=str(e),
            ) from e

    async def deactivate_user(self, user: TUser, password: str | None = None) -> TUser:
        """
        Deactivate a user and revoke all of their sessions.
        """
        try:
            if not user.is_active():
                raise ConflictException(
                    error="User is already deactivated.",
                    errors={"code": "USER_ALREADY_DEACTIVATED"},
                )

            if password:
                account = await self._account_service.get_account_by(
                    user_id=user.id, type="credentials"
                )
                if not account or not account.hashed_password:
                    self._account_service._hash_service.dummy_verify(password)
                    raise InvalidException(
                        error="Invalid password.",
                        errors={"password": "Invalid password."},
                    )
                if not self._account_service._hash_service.verify(
                    account.hashed_password, password
                ):
                    raise InvalidException(
                        error="Invalid password.",
                        errors={"password": "Invalid password."},
                    )

            user.status = "inactive"
            updated_user = await self.update_user(user)

            await self._session_service.invalidate_user_sessions(user_id=user.id)

            await event_bus.publish(
                UserDeactivatedEvent(
                    user_id=user.id,
                    email=user.email,
                    user_uuid=user.uuid,
                )
            )
            return updated_user
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to deactivate user.",
                internal_details=str(e),
            ) from e

    async def get_user_by(self, **kwargs) -> TUser | None:
        """
        Retrieve a user instance based on provided keyword arguments.
        """
        try:
            return await self._repository.get_by(**kwargs)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve user.",
                internal_details=str(e),
            ) from e

    async def get_users_by_ids(self, ids: list[int]) -> list[TUser]:
        """
        Retrieve multiple users by their internal integer ids in a single query.

        Used by the boundary layer to resolve batches of members to their
        public uuids without an N+1 lookup per member.
        """
        try:
            return await self._repository.get_by_ids(ids)
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to retrieve users.",
                internal_details=str(e),
            ) from e

    async def _create_user_session(
        self,
        user_id: int,
        expire_minutes: int,
        device: str,
        ip_address: str,
        browser: str,
    ) -> TSession:
        """
        Create a new user session.
        """
        try:
            session = await self._session_service.create_session(
                user_id=user_id,
                expire_minutes=expire_minutes,
                device=device,
                ip_address=ip_address,
                browser=browser,
            )
            return session
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to create user session.",
                internal_details=str(e),
            ) from e

    async def get_email_verification_token(
        self, user_id: int, email_token_expiry_minutes: int, email_token_digit: int
    ) -> tuple[TToken, str]:
        """
        Generate an email verification token for the specified user.
        """
        try:
            token = self._random_token(digit=email_token_digit)
            email_token = await self._token_service.create_token(
                user_id=user_id,
                type="email_verification",
                token_hash=self._account_service._hash_service.deterministic_hash(
                    token
                ),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=email_token_expiry_minutes),
            )
            return email_token, token
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to generate email verification token.",
                internal_details=str(e),
            ) from e

    async def get_password_reset_token(
        self,
        user_id: int,
        password_reset_token_expiry_minutes: int,
        password_reset_token_digit: int,
    ) -> tuple[TToken, str]:
        """
        Generate a password reset token for the specified user.
        """
        try:
            token = self._random_token(digit=password_reset_token_digit)
            password_reset_token = await self._token_service.create_token(
                user_id=user_id,
                type="password_reset",
                token_hash=self._account_service._hash_service.deterministic_hash(
                    token
                ),
                expires_at=datetime.now(UTC)
                + timedelta(minutes=password_reset_token_expiry_minutes),
            )
            return password_reset_token, token
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to generate password reset token.",
                internal_details=str(e),
            ) from e

    def _random_token(self, digit: int = 6) -> str:
        """
        Generates a cryptographically secure random numeric token with the
        specified number of digits (used for short, user-typed OTP codes such
        as email verification). Uses `secrets` rather than `random` so the
        value is not predictable.
        """
        import secrets

        range_start = 10 ** (digit - 1)
        range_end = (10**digit) - 1
        span = range_end - range_start + 1
        return str(range_start + secrets.randbelow(span))


def get_auth_user_service(
    *,
    session: AsyncSession,
    user_model: type[TUser],
    account_model: type[TAccount],
    session_model: type[TSession],
    token_model: type[TToken],
) -> AuthUserService[TUser, TSession, TToken]:
    """
    Factory function to create an instance of AuthUserService.

    :param session: An instance of AsyncSession for database operations.
    :return: An instance of AuthUserService.
    """
    repository = AuthUserRepository(session=session, model=user_model)
    user_account_service = get_auth_user_account_service(
        session=session, model=account_model
    )
    user_session_service = get_auth_user_session_service(
        session=session, model=session_model
    )
    user_token_service = get_auth_user_tokens_service(
        session=session, model=token_model
    )
    return AuthUserService(
        repository=repository,
        model=user_model,
        account_service=user_account_service,
        session_service=user_session_service,
        token_service=user_token_service,
    )
