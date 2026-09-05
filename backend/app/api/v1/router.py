"""
Aggregates all v1 API routers into a single APIRouter.

Design decision: each domain (auth, admin, patients, medical history,
medications, predictions, vitals, alerts, notifications, reports, ...)
gets its OWN router module. This file only combines them — it contains no
business logic.

There is no doctor role in this system, so there is no doctors/
appointments/messages router — patient-facing "messaging" is the AI
Health Assistant (see api/v1/assistant.py, Phase 3).
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    alerts,
    assistant,
    auth,
    disease_assessments,
    medical_history,
    medications,
    model_info,
    notifications,
    patients,
    predictions,
    reports,
    vitals,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(medical_history.router, prefix="/patients", tags=["Medical History"])
api_router.include_router(medications.router, prefix="", tags=["Medications"])
api_router.include_router(predictions.router, prefix="/patients", tags=["AI Risk Predictions"])
api_router.include_router(vitals.router, prefix="/patients", tags=["Vitals"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reports.router, prefix="/patients", tags=["Reports"])
api_router.include_router(disease_assessments.router, prefix="/patients", tags=["Disease Assessments"])
api_router.include_router(assistant.router, prefix="/patients", tags=["AI Health Assistant"])
api_router.include_router(model_info.router, prefix="/model-info", tags=["AI Model Transparency"])
