"""
Report routes — PDF generation. Follows the standard patient-access rule:
self or admin.
"""

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.authorization import ensure_patient_access
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.services.patient_service import PatientService
from app.services.report_service import ReportService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(db)


@router.get("/{patient_id}/reports/summary")
def get_patient_summary_report(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    report_service: ReportService = Depends(get_report_service),
):
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)

    pdf_bytes = report_service.generate_patient_summary(patient_id)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="patient_summary_{patient_id}.pdf"'},
    )


@router.get("/{patient_id}/reports/vitals-history")
def get_vitals_history_csv(
    patient_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    patient_service: PatientService = Depends(get_patient_service),
    report_service: ReportService = Depends(get_report_service),
):
    """Downloads the patient's complete vitals history as a CSV file."""
    try:
        patient = patient_service.get_by_id(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    ensure_patient_access(current_user, patient)

    csv_bytes = report_service.generate_vitals_history_csv(patient_id)
    safe_name = patient.user.full_name.replace(" ", "_").lower() or "patient"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_vitals_history.csv"'
        },
    )
