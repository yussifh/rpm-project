"""
Auth routes.

Design decision: /login uses OAuth2PasswordRequestForm (form-encoded
username/password) rather than a JSON body, specifically so this API
stays compatible with FastAPI's built-in Swagger "Authorize" button and
any standard OAuth2 client tooling — `username` field carries the email.
"""

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.db.redis_client import get_redis
from app.models.user import User
from app.schemas.token import AccessTokenResponse, Token
from app.schemas.user import ChangePasswordRequest, UserOut
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)) -> AuthService:
    return AuthService(db, redis_client)


# NOTE: There is deliberately no public self-registration endpoint here.
# Every patient account is created by an admin (POST /admin/users/patient)
# — matching the workflow where a patient is always onboarded by staff,
# not a stranger creating their own account and self-assigning a diagnosis.


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    import logging
    logging.getLogger("uvicorn.error").info(
        "DEBUG-LOGIN email=%r email_len=%d pw_len=%d",
        form_data.username, len(form_data.username or ""), len(form_data.password or ""),
    )
    try:
        user = auth_service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    access_token, refresh_token = auth_service.issue_tokens(user)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        new_access_token = auth_service.refresh_access_token(refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AccessTokenResponse(access_token=new_access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revokes the given refresh token. Idempotent — logging out twice,
    or with an already-expired token, is not an error."""
    auth_service.revoke_refresh_token(refresh_token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/password", response_model=UserOut)
def change_my_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return auth_service.change_password(current_user, payload.current_password, payload.new_password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
