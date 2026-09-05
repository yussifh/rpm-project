"""
Notification — lightweight, per-user inbox item (distinct from Alert).

Design decision: Alerts are CLINICAL events tied to a patient's health data
and have a resolution lifecycle. Notifications are generic UI inbox items
(e.g. "Your appointment was confirmed", "New message from Dr. Smith") that
any user role can receive. Keeping them separate avoids overloading the
Alert model with non-clinical UI concerns.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "appointment", "alert", "system"
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Relationships ---
    user: Mapped["User"] = relationship(back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} - read={self.is_read}>"
