"""
Alert schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AlertSeverity, AlertStatus


class AlertOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    related_vital_id: uuid.UUID | None
    related_prediction_id: uuid.UUID | None
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    emergency_contact_notified: bool
    created_at: datetime

    model_config = {"from_attributes": True}
