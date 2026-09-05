"""
Token schemas — response/payload shapes for the auth flow.
"""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Returned by /auth/refresh — only a new access token, refresh token unchanged."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str          # user id
    role: str
    type: str
    jti: str | None = None
