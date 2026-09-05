"""
Model-info routes — static, per-disease AI model transparency data.

Deliberately NOT nested under /patients/{patient_id}: this data (metrics,
feature importances, data provenance) describes the MODEL, not any one
patient's prediction. Any authenticated user can read it — it's the same
information for every request, and hiding it behind stricter roles would
work against the whole point of it (transparency).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_db, require_roles
from app.core.exceptions import InsufficientDataError
from app.models.enums import DiseaseType, UserRole
from app.models.user import User
from app.schemas.prediction import ModelInfoOut
from app.services.prediction_service import PredictionService
from sqlalchemy.orm import Session

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_prediction_service(db: Session = Depends(get_db)) -> PredictionService:
    return PredictionService(db)


@router.get("/{disease_type}", response_model=ModelInfoOut)
def get_model_info(
    disease_type: DiseaseType,
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    try:
        return prediction_service.get_model_info(disease_type)
    except InsufficientDataError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
