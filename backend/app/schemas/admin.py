"""
Schemas for admin-initiated account creation and user management.
"""

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Gender


class _PasswordValidatorMixin(BaseModel):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class AdminCreateRequest(_PasswordValidatorMixin):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone_number: str | None = None
    department: str | None = None
    job_title: str | None = None
    is_super_admin: bool = False


class PatientCreateRequest(_PasswordValidatorMixin):
    """Lets an admin create a patient account directly (in addition to the
    existing public self-registration flow) — e.g. onboarding a patient
    over the phone or in-clinic who can't self-register right away."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    phone_number: str | None = None
    date_of_birth: date
    gender: Gender
    blood_group: str | None = None
