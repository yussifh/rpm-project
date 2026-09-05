"""
Shared API dependencies: DB/Redis injection, current-user resolution from
the JWT access token, and role-based access control (RBAC) guards.

Design decision: `require_roles(*roles)` is a dependency FACTORY, not a
single dependency. This means route definitions read declaratively, e.g.:

    @router.get("/admin-only", dependencies=[Depends(require_roles(UserRole.ADMIN))])

RBAC is enforced here, before the request ever reaches a route handler's
business logic — a controller can never accidentally "forget" to check
a role, because the check happens at the dependency-injection layer.
"""

import uuid

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import JWTError, TokenType, decode_token
from app.db.redis_client import get_redis
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != TokenType.ACCESS.value:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        raise credentials_exception

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory — restricts a route to one or more roles."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _guard


# Re-exported for convenience in route modules
__all__ = ["get_current_user", "require_roles", "get_db", "get_redis"]
