"""
User schemas — request/response shapes for auth and user-facing endpoints.

Design decision: `UserOut` never includes `hashed_password` — Pydantic
schemas are the API's contract boundary, so excluding sensitive fields here
means there's no risk of accidentally serializing a password hash into a
JSON response, even if a future endpoint carelessly returns the full ORM
object.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Gender, UserRole


class PatientRegisterRequest(BaseModel):
    """
    Public self-registration is PATIENT-ONLY by design. Admin
    accounts are created by an existing Admin via a protected endpoint
    (Module 4 — User Management), since granting medical/administrative
    access shouldn't be as simple as filling out a public signup form.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    phone_number: str | None = None

    date_of_birth: date
    gender: Gender
    blood_group: str | None = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserUpdate(BaseModel):
    """Admin-only edit of a user's core identity fields. All optional
    (PATCH semantics) — admin corrects a typo without resending everything."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone_number: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone_number: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
