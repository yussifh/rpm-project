"""
AssistantMessage — persisted turn-by-turn history for the AI Health
Assistant chat (see app.services.assistant_service).

Design decision: this replaces what used to be patient<->doctor
messaging (removed along with the doctor role). Storing history serves
two purposes: (1) the chat UI needs it to render past turns on reload,
and (2) it's an audit trail of exactly what the AI told a patient — which
matters for a healthcare-adjacent feature, in the same spirit as
RiskPrediction storing `input_features`/`reasons` for traceability.

`role` distinguishes the patient's own message from the assistant's
reply, mirroring the shape LLM chat APIs already use (user/assistant),
so history can be replayed directly as conversation context on the next
call without reshaping it.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin
from app.models.types import PortableUUID


class AssistantMessage(Base, TimestampMixin):
    __tablename__ = "assistant_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # True when this assistant reply was the deterministic emergency
    # override (see assistant_service.py) rather than an LLM-generated
    # response — kept for audit clarity, so it's always possible to tell
    # which replies came from the safety rule vs. the model.
    is_emergency_override: Mapped[bool] = mapped_column(default=False, nullable=False)

    # --- Relationships ---
    patient: Mapped["PatientProfile"] = relationship()

    def __repr__(self) -> str:
        return f"<AssistantMessage {self.role} patient={self.patient_id}>"
