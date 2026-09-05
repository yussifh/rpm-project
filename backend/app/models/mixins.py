"""
Reusable mixins for ORM models.

Design decision: rather than repeating created_at/updated_at columns on
every model, we use a mixin (composition over duplication). Every table
that inherits TimestampMixin automatically gets audit-friendly timestamps
managed by the database itself (server_default / onupdate), not by
application code — this guarantees consistency even if a row is modified
outside the API (e.g. a manual SQL fix).
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
