"""
AssistantMessageRepository — data access for `assistant_messages`.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assistant_message import AssistantMessage


class AssistantMessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_patient(self, patient_id: uuid.UUID, limit: int = 200) -> list[AssistantMessage]:
        stmt = (
            select(AssistantMessage)
            .where(AssistantMessage.patient_id == patient_id)
            .order_by(AssistantMessage.created_at.asc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_recent_for_patient(self, patient_id: uuid.UUID, limit: int = 10) -> list[AssistantMessage]:
        """Most recent N messages, oldest-first — used to build LLM
        conversation context without sending the entire history on every
        call."""
        stmt = (
            select(AssistantMessage)
            .where(AssistantMessage.patient_id == patient_id)
            .order_by(AssistantMessage.created_at.desc())
            .limit(limit)
        )
        recent = list(self.db.execute(stmt).scalars().all())
        return list(reversed(recent))

    def create(self, message: AssistantMessage) -> AssistantMessage:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
