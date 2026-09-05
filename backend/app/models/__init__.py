"""
Importing every model here ensures they're all registered on Base.metadata
before Alembic's autogenerate (or Base.metadata.create_all in tests) runs.
Without this, tables defined in files never imported elsewhere would
silently be skipped from migrations.
"""

from app.models.user import User
from app.models.admin import AdminProfile
from app.models.patient import PatientProfile
from app.models.vitals import VitalReading
from app.models.prediction import RiskPrediction
from app.models.alert import Alert
from app.models.medication import Medication, MedicationLog
from app.models.medical_history import MedicalHistoryEntry
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.disease_assessment import DiseaseAssessment
from app.models.assistant_message import AssistantMessage

__all__ = [
    "User",
    "AdminProfile",
    "PatientProfile",
    "VitalReading",
    "RiskPrediction",
    "Alert",
    "Medication",
    "MedicationLog",
    "MedicalHistoryEntry",
    "Notification",
    "AuditLog",
    "DiseaseAssessment",
    "AssistantMessage",
]
