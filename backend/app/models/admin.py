"""
AdminProfile — admin-specific data, 1:1 with User where role == ADMIN.

Design decision: mirrors the PatientProfile pattern for consistency, even
though admins need far fewer fields. `is_super_admin` distinguishes a
small set of unrestricted accounts (e.g. system owner) from regular
admins whose actions can be scoped via `permissions` — a JSONB array of
permission strings (e.g. ["manage_patients", "view_audit_logs"]).
This gives room for granular access control later without a schema change,
while the base `role` enum on User still handles the coarse admin/
patient split used for primary route-level RBAC.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin
from app.models.types import PortableJSON, PortableUUID


class AdminProfile(Base, TimestampMixin):
    __tablename__ = "admin_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)

    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Fine-grained permission scopes for non-super admins, e.g.
    # ["manage_patients", "manage_ml_models", "view_audit_logs"]
    permissions: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="admin_profile")

    def __repr__(self) -> str:
        return f"<AdminProfile {self.job_title or 'Admin'} super={self.is_super_admin}>"
