"""
Centralized enums shared across ORM models, Pydantic schemas, and services.

Design decision: enums live in ONE place (not redefined per-model) so that
role names, disease types, and status values can't drift between the DB
layer, API layer, and frontend TypeScript types. When the frontend types
are generated later, these values are the single source of truth.
"""

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PATIENT = "patient"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class DiseaseType(str, enum.Enum):
    STROKE = "stroke"
    DIABETES = "diabetes"
    HYPERTENSION = "hypertension"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class MedicationStatus(str, enum.Enum):
    TAKEN = "taken"
    MISSED = "missed"
    SKIPPED = "skipped"


class VitalSource(str, enum.Enum):
    MANUAL = "manual"          # patient self-reported
    DEVICE = "device"          # connected wearable/monitor (future integration)
    CLINIC = "clinic"          # entered by clinic staff during an in-person visit
