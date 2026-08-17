from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    generate_refresh_token_value,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.enums import RegistrationStatus, UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.registration_repository import RegistrationRequestRepository
from app.repositories.resident_repository import ResidentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import PasswordChange, ProfileUpdate, TokenResponse, UserCreate


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.residents = ResidentRepository(session)
        self.registration_requests = RegistrationRequestRepository(session)

    async def register_user(self, data: UserCreate) -> User:
        existing = await self.users.get_by_email(data.email)
        if existing:
            raise ConflictError("A user with this email already exists")

        if data.role == UserRole.RESIDENT:
            resident = await self.residents.get(data.resident_id)
            if not resident:
                raise NotFoundError("No resident profile found for resident_id")
            existing_login = await self.users.get_by_resident_id(data.resident_id)
            if existing_login:
                raise ConflictError("This resident already has a login account")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            resident_id=data.resident_id,
        )
        return await self.users.create(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user and user.is_active and verify_password(password, user.hashed_password):
            return user

        # No active account under this email. Check for a self-registration
        # application so we can say *why* rather than a bare "invalid
        # credentials" — but only once we've confirmed they know the right
        # password for that application, so this can't be used to probe
        # arbitrary emails for their application status.
        application = await self.registration_requests.latest_for_email(email)
        if application and verify_password(password, application.hashed_password):
            if application.status == RegistrationStatus.PENDING:
                raise AuthError("Your registration is still awaiting admin approval")
            if application.status == RegistrationStatus.REJECTED:
                detail = f": {application.review_note}" if application.review_note else ""
                raise AuthError(f"Your registration was not approved{detail}")

        raise AuthError("Invalid email or password")

    async def issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(str(user.id), extra_claims={"role": user.role.value})
        raw_refresh = generate_refresh_token_value()
        record = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=refresh_token_expiry(),
        )
        await self.refresh_tokens.create(record)
        return TokenResponse(access_token=access_token, refresh_token=raw_refresh)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        """Rotates the refresh token: the presented token is atomically
        revoked and replaced. If a token that's already revoked is presented
        again, that's a signal of theft/replay, so we revoke the entire
        chain for that user to kill the session outright.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        record = await self.refresh_tokens.get_by_token_hash(token_hash)
        if not record:
            raise AuthError("Invalid refresh token")

        if record.revoked:
            await self.refresh_tokens.revoke_all_for_user(record.user_id)
            # Commit the revocation now: this request is about to fail with
            # AuthError, and get_session rolls back on any exception, which
            # would otherwise silently undo the very revocation meant to
            # shut the session down.
            await self.session.commit()
            raise AuthError("Refresh token reuse detected; session revoked")

        # Some DB drivers (notably SQLite, used in tests) don't round-trip
        # tzinfo even on a timezone-aware column; values we write are always
        # UTC (see refresh_token_expiry), so a naive value read back is safe
        # to treat as UTC rather than erroring on an aware/naive comparison.
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise AuthError("Refresh token expired")

        user = await self.users.get(record.user_id)
        if not user or not user.is_active:
            raise AuthError("User is not active")

        new_tokens = await self.issue_tokens(user)
        # Link rotation chain and revoke the used token.
        latest = await self.refresh_tokens.get_by_token_hash(
            hash_refresh_token(new_tokens.refresh_token)
        )
        record.revoked = True
        record.replaced_by_id = latest.id if latest else None
        self.session.add(record)
        await self.session.flush()

        return new_tokens

    async def update_profile(self, user: User, data: ProfileUpdate) -> User:
        changes = data.model_dump(exclude_unset=True)
        if "email" in changes and changes["email"] != user.email:
            existing = await self.users.get_by_email(changes["email"])
            if existing:
                raise ConflictError("A user with this email already exists")
        return await self.users.update(user, changes)

    async def change_password(self, user: User, data: PasswordChange) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise AuthError("Current password is incorrect")
        await self.users.update(user, {"hashed_password": hash_password(data.new_password)})
        # A password change is a security-sensitive event — kill every other
        # session so a possibly-compromised refresh token stops working too,
        # not just the one the user is currently using.
        await self.refresh_tokens.revoke_all_for_user(user.id)

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        record = await self.refresh_tokens.get_by_token_hash(token_hash)
        if record and not record.revoked:
            record.revoked = True
            self.session.add(record)
            await self.session.flush()
