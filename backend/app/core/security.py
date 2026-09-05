"""
Core security primitives: password hashing (bcrypt) and JWT issuance/
verification (JWT + OAuth2 password flow).

Design decisions:
- Passwords are hashed with bcrypt via passlib's CryptContext — never
  compared or stored in plaintext, and bcrypt's built-in salt means two
  identical passwords never produce the same hash.
- TWO token types are issued: a short-lived ACCESS token (stateless, used
  on every request, never touches the DB/Redis to verify) and a longer-
  lived REFRESH token (tracked in Redis by its `jti` claim). This hybrid
  approach is deliberate for a healthcare system: access tokens stay fast
  and stateless for normal API calls, while refresh tokens are revocable
  (e.g. an admin deactivating a compromised account, or a user logging
  out) — something a purely stateless JWT scheme cannot do.
- `jti` (JWT ID) is a random UUID embedded in refresh tokens so each one
  can be individually looked up / deleted in Redis without affecting a
  user's other active sessions (e.g. logged in on two devices).
"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


# --- Password hashing ---

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT creation ---

def _create_token(subject: str, role: str, token_type: TokenType, expires_delta: timedelta) -> tuple[str, str]:
    """Returns (encoded_jwt, jti). jti is only meaningful for refresh tokens."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,       # user id
        "role": role,
        "type": token_type.value,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    encoded = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti


def create_access_token(user_id: str, role: str) -> str:
    token, _ = _create_token(
        subject=user_id,
        role=role,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return token


def create_refresh_token(user_id: str, role: str) -> tuple[str, str, int]:
    """Returns (token, jti, expires_in_seconds) — jti/expiry needed by the
    caller to register the token in Redis for revocation tracking."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token, jti = _create_token(
        subject=user_id,
        role=role,
        token_type=TokenType.REFRESH,
        expires_delta=expires_delta,
    )
    return token, jti, int(expires_delta.total_seconds())


def decode_token(token: str) -> dict:
    """Raises jose.JWTError if the token is invalid, expired, or tampered with."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


__all__ = [
    "TokenType",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "JWTError",
]
