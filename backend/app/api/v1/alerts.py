"""
Alert routes.

There is no POST/create endpoint here on purpose — alerts are only ever
created internally by VitalsService (see its module docstring). There is
no doctor role: patients can view their own alerts; only admin can
acknowledge/resolve (see AlertService docstring).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.exceptions import InsufficientPermissionsError, NotFoundError
from app.models.enums import AlertStatus, UserRole
from app.models.user import User
from app.schemas.alert import AlertOut
from app.services.alert_service import AlertService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.PATIENT))])


def get_alert_service(db: Session = Depends(get_db)) -> AlertService:
    return AlertService(db)


@router.get("", response_model=list[AlertOut])
def list_my_alerts(
    status_filter: AlertStatus | None = None,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """Admin sees all alerts; patient sees alerts about themself."""
    return service.list_for_current_user(current_user, status=status_filter)


@router.patch(
    "/{alert_id}/acknowledge",
    response_model=AlertOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def acknowledge_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    try:
        return service.acknowledge(alert_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientPermissionsError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def resolve_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    try:
        return service.resolve(alert_id, current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientPermissionsError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
