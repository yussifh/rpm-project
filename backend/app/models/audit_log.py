"""
AuditLog — immutable trail of every significant state-changing action in
the system (a compliance requirement for healthcare-adjacent software,
modeled after HIPAA-style audit trail expectations).

Design decision:
  - No `updated_at` / no update path at the service layer — audit logs are
    INSERT-ONLY by design. Nothing in the application should ever UPDATE
    or DELETE a row here.
  - `user_id` is nullable to still capture system-initiated actions (e.g.
    an automated AI alert) that weren't triggered by a logged-in user.
  - `metadata` (JSONB) holds the flexible "what changed" payload so this
    single table can audit ANY entity type without schema changes.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.types import PortableJSON, PortableUUID


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g. "CREATE_PATIENT"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g. "PatientProfile"
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6-safe length
    extra_metadata: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
