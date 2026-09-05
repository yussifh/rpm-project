"""
AuthService — business logic for registration, authentication, and token
lifecycle. Routers call this service; the service calls the repository
(for DB) and Redis (for refresh-token tracking). No SQL and no HTTP
concerns live here.

Refresh-token revocation design: each refresh token's `jti` is stored in
Redis as key `refresh_token:{jti}` -> user_id, with a TTL matching the
token's own expiry. This makes revocation (logout) an O(1) Redis DELETE,
and lets /auth/refresh confirm a token hasn't been revoked before issuing
a new access token — something impossible with a purely stateless JWT.
"""

import uuid

import redis
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.security import (
    JWTError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.patient import PatientProfile
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import PatientRegisterRequest

REFRESH_TOKEN_KEY_PREFIX = "refresh_token:"


class AuthService:
    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.users = UserRepository(db)

    # --- Registration ---

    def register_patient(self, data: PatientRegisterRequest) -> User:
        if self.users.get_by_email(data.email):
            raise DuplicateEmailError(data.email)

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone_number=data.phone_number,
            role=UserRole.PATIENT,
        )
        user.patient_profile = PatientProfile(
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            blood_group=data.blood_group,
        )
        return self.users.create(user)

    # --- Authentication ---

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()
        user.hashed_password = hash_password(new_password)
        return self.users.create(user)  # create() does add+commit+refresh; safe for updates too

    # --- Token issuance ---

    def issue_tokens(self, user: User) -> tuple[str, str]:
        """Returns (access_token, refresh_token). Registers the refresh
        token's jti in Redis so it can later be revoked on logout."""
        access_token = create_access_token(str(user.id), user.role.value)
        refresh_token, jti, expires_in = create_refresh_token(str(user.id), user.role.value)

        self.redis.set(f"{REFRESH_TOKEN_KEY_PREFIX}{jti}", str(user.id), ex=expires_in)
        return access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> str:
        payload = self._decode_and_validate(refresh_token, expected_type=TokenType.REFRESH)

        jti = payload.get("jti")
        redis_key = f"{REFRESH_TOKEN_KEY_PREFIX}{jti}"
        stored_user_id = self.redis.get(redis_key)
        if stored_user_id is None:
            raise InvalidTokenError("Refresh token has been revoked or expired")

        user = self.users.get_by_id(uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise InvalidTokenError("User no longer active")

        return create_access_token(str(user.id), user.role.value)

    def revoke_refresh_token(self, refresh_token: str) -> None:
        """Used for logout. Silently no-ops on an already-invalid token —
        logging out with a stale token should never itself be an error."""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            return
        jti = payload.get("jti")
        if jti:
            self.redis.delete(f"{REFRESH_TOKEN_KEY_PREFIX}{jti}")

    # --- Internal helpers ---

    def _decode_and_validate(self, token: str, expected_type: TokenType) -> dict:
        try:
            payload = decode_token(token)
        except JWTError:
            raise InvalidTokenError()

        if payload.get("type") != expected_type.value:
            raise InvalidTokenError(f"Expected a {expected_type.value} token")

        try:
            uuid.UUID(payload.get("sub", ""))
        except (ValueError, TypeError):
            raise InvalidTokenError()

        return payload
