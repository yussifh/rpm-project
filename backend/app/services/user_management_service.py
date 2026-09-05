"""
UserManagementService — admin-only operations: creating Patient/Admin
accounts, listing users, and activating/deactivating accounts.

Design decision: this service is intentionally separate from AuthService.
AuthService handles SELF-SERVICE identity actions (login, register-as-
patient, refresh, logout). UserManagementService handles ADMIN-ACTING-ON-
OTHERS actions. Splitting them keeps each service's authorization story
simple: every method here assumes the caller has already been confirmed
as ADMIN by the router's RBAC dependency.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateEmailError, NotFoundError
from app.core.security import hash_password
from app.models.admin import AdminProfile
from app.models.enums import UserRole
from app.models.patient import PatientProfile
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import AdminCreateRequest, PatientCreateRequest
from app.schemas.patient import PatientProfileUpdate
from app.schemas.user import UserUpdate
from app.services.audit_service import AuditService


class UserManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.patients = PatientRepository(db)
        self.audit = AuditService(db)

    def create_patient(self, data: PatientCreateRequest, actor_user_id: uuid.UUID | None = None) -> User:
        if self.users.get_by_email(data.email):
            raise DuplicateEmailError(data.email)

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone_number=data.phone_number,
            role=UserRole.PATIENT,
            is_verified=True,  # admin-created accounts are pre-verified
        )
        user.patient_profile = PatientProfile(
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            blood_group=data.blood_group,
        )
        created = self.users.create(user)
        self.audit.log(
            action="CREATE_PATIENT",
            entity_type="User",
            entity_id=created.id,
            user_id=actor_user_id,
            metadata={"email": created.email},
        )
        return created

    def create_admin(self, data: AdminCreateRequest, actor_user_id: uuid.UUID | None = None) -> User:
        if self.users.get_by_email(data.email):
            raise DuplicateEmailError(data.email)

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone_number=data.phone_number,
            role=UserRole.ADMIN,
            is_verified=True,
        )
        user.admin_profile = AdminProfile(
            department=data.department,
            job_title=data.job_title,
            is_super_admin=data.is_super_admin,
        )
        created = self.users.create(user)
        self.audit.log(
            action="CREATE_ADMIN",
            entity_type="User",
            entity_id=created.id,
            user_id=actor_user_id,
            metadata={"email": created.email},
        )
        return created

    def list_users(self, role: UserRole | None = None) -> list[User]:
        return self.users.list_all(role=role)

    def set_active_status(
        self, user_id: uuid.UUID, is_active: bool, actor_user_id: uuid.UUID | None = None
    ) -> User:
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))
        user.is_active = is_active
        updated = self.users.create(user)  # create() does add+commit+refresh; safe for updates too
        self.audit.log(
            action="ACTIVATE_USER" if is_active else "DEACTIVATE_USER",
            entity_type="User",
            entity_id=user_id,
            user_id=actor_user_id,
        )
        return updated

    def update_user_details(
        self, user_id: uuid.UUID, data: UserUpdate, actor_user_id: uuid.UUID | None = None
    ) -> User:
        """Admin edit of a user's core identity fields (name/email/phone)."""
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))

        updates = data.model_dump(exclude_unset=True)
        if "email" in updates and updates["email"].lower() != user.email:
            existing = self.users.get_by_email(updates["email"])
            if existing and existing.id != user.id:
                raise DuplicateEmailError(updates["email"])
            updates["email"] = updates["email"].lower()

        for field, value in updates.items():
            setattr(user, field, value)

        updated = self.users.create(user)  # create() does add+commit+refresh; safe for updates too
        self.audit.log(
            action="UPDATE_USER",
            entity_type="User",
            entity_id=user_id,
            user_id=actor_user_id,
            metadata={"fields": list(updates.keys())},
        )
        return updated

    def update_patient_profile(
        self, patient_id: uuid.UUID, data: PatientProfileUpdate, actor_user_id: uuid.UUID | None = None
    ) -> PatientProfile:
        """Admin edit of a patient's medical profile fields."""
        patient = self.patients.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("PatientProfile", str(patient_id))

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(patient, field, value)

        updated = self.patients.save(patient)
        self.audit.log(
            action="UPDATE_PATIENT_PROFILE",
            entity_type="PatientProfile",
            entity_id=patient_id,
            user_id=actor_user_id,
            metadata={"fields": list(updates.keys())},
        )
        return updated
