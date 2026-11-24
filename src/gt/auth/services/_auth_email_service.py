from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from gt.auth.errors import AuthErrorCode
from gt.auth.events import UserEmailVerifiedEvent, event_bus
from gt.auth.events._auth_events import UserEmailVerificationResentEvent
from gt.auth.models._auth_user_model import AuthUserModel, TUser
from gt.auth.models._auth_user_tokens_model import AuthUserTokensModelBase
from gt.auth.repositories._auth_user_account_repository import TAccount
from gt.auth.repositories._auth_user_session_repository import TSession
from gt.auth.repositories._auth_user_tokens_repository import TToken
from gt.auth.services._auth_user_service import AuthUserService, get_auth_user_service
from gt.auth.services._auth_user_tokens_service import AuthUserTokensService
from gt.auth.services.hash._hash_service import HasherService
from gt.exceptions._base_exceptions import (
    ConflictException,
    DomainException,
    InvalidException,
    NotFoundException,
)


class AuthEmailService[TUser: AuthUserModel, TToken: AuthUserTokensModelBase]:
    """
    Service class for handling email verification operations.
    """

    def __init__(
        self,
        user_service: AuthUserService,
        token_service: AuthUserTokensService[TToken],
        hash_service: HasherService,
    ):
        self._user_service = user_service
        self._token_service = token_service
        self._hash_service = hash_service

    async def verify_email(self, user: TUser, token: str) -> TUser:
        """
        Verify a user's email address using a verification token.
        """
        try:
            if user.is_email_verified():
                raise ConflictException(
                    error="Email is already verified.",
                    errors={"code": AuthErrorCode.EMAIL_ALREADY_VERIFIED},
                )

            token_record = await self._token_service.get_token_by(
                user_id=user.id,
                type="email_verification",
                used_at=None,
            )
            if not token_record:
                raise NotFoundException(
                    error="No verification token found. Request a new one.",
                    errors={"token": "Invalid or expired token."},
                )

            if token_record.expires_at < datetime.now(UTC):
                raise InvalidException(
                    error="Verification token has expired. Request a new one.",
                    errors={"token": "Invalid or expired token."},
                )

            if not self._hash_service.verify_deterministic_hash(
                token, token_record.token_hash
            ):
                raise InvalidException(
                    error="Invalid verification token.",
                    errors={"token": "Invalid or expired token."},
                )

            token_record.used_at = datetime.now(UTC)
            await self._token_service.update_token(token_record)

            user.email_verified_at = datetime.now(UTC)
            await self._user_service.update_user(user)

            await event_bus.publish(
                UserEmailVerifiedEvent(
                    user_id=user.id,
                    email=user.email,
                    user_uuid=user.uuid,
                )
            )
            return user
        except (
            NotFoundException,
            ConflictException,
            InvalidException,
            DomainException,
        ):
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to verify email.",
                internal_details=str(e),
            ) from e

    async def resend_verification_email(
        self, user: TUser, email_token_expiry_minutes: int, email_token_digit: int
    ) -> None:
        """
        Resend the email verification token to the user.
        """
        try:
            if user.is_email_verified():
                raise ConflictException(
                    error="Email is already verified.",
                    errors={"code": AuthErrorCode.EMAIL_ALREADY_VERIFIED},
                )

            await self._token_service.delete_tokens_by(
                user_id=user.id,
                type="email_verification",
            )

            _, plain_token = await self._user_service.get_email_verification_token(
                user_id=user.id,
                email_token_digit=email_token_digit,
                email_token_expiry_minutes=email_token_expiry_minutes,
            )

            await event_bus.publish(
                UserEmailVerificationResentEvent(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    user_uuid=user.uuid,
                    email_token=plain_token,
                    email_token_expiry_minutes=email_token_expiry_minutes,
                )
            )
        except DomainException:
            raise
        except Exception as e:
            raise DomainException(
                error="Failed to resend verification email.",
                internal_details=str(e),
            ) from e


def get_auth_email_service(
    *,
    session: AsyncSession,
    user_model: type[TUser],
    account_model: type[TAccount],
    session_model: type[TSession],
    token_model: type[TToken],
) -> AuthEmailService[TUser, TToken]:
    """
    Factory function to create an instance of AuthEmailService.
    """
    from gt.auth.services._auth_user_tokens_service import (
        get_auth_user_tokens_service,
    )

    user_service = get_auth_user_service(
        session=session,
        user_model=user_model,
        account_model=account_model,
        session_model=session_model,
        token_model=token_model,
    )
    token_service = get_auth_user_tokens_service(session=session, model=token_model)
    hash_service = HasherService()
    return AuthEmailService(
        token_service=token_service,
        hash_service=hash_service,
        user_service=user_service,
    )
