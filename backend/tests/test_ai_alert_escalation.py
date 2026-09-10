"""Tests for the confirmation-over-time AI-alert escalation gate — the
logic that prevents low-precision stroke/hypertension models from firing
a CRITICAL (emergency-contact-escalating) alert on a single reading."""

from datetime import date, datetime, timezone

from app.models.enums import DiseaseType, RiskLevel
from app.models.patient import PatientProfile
from app.models.prediction import RiskPrediction
from app.models.user import User
from app.services.vitals_service import VitalsService
from tests.conftest import seed_admin


def _make_patient(db_session, email="conf@example.com"):
    seed_admin(db_session)
    user = User(
        email=email,
        hashed_password="x",
        full_name="Confirmation Pt",
        role="patient",
        is_active=True,
        is_verified=True,
    )
    user.patient_profile = PatientProfile(date_of_birth=date(1945, 5, 5), gender="male")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user.patient_profile


def _make_prediction(db_session, patient, disease, risk_level):
    pred = RiskPrediction(
        patient_id=patient.id,
        disease_type=disease,
        risk_score=0.8,
        risk_level=risk_level,
        model_version="test",
        data_source="test",
        input_features={},
        reasons=[],
        recommendations=[],
        predicted_at=datetime.now(timezone.utc),
    )
    db_session.add(pred)
    db_session.commit()
    db_session.refresh(pred)
    return pred


def _service(db_session):
    return VitalsService(db_session)


def test_previous_prediction_was_elevated_true_when_prior_is_high(db_session):
    patient = _make_patient(db_session)
    prev = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.HIGH)
    current = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.CRITICAL)
    svc = _service(db_session)
    assert svc._previous_prediction_was_elevated(patient.id, DiseaseType.STROKE, current.id) is True


def test_previous_prediction_was_elevated_false_when_prior_is_low(db_session):
    patient = _make_patient(db_session)
    prev = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.LOW)
    current = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.CRITICAL)
    svc = _service(db_session)
    assert svc._previous_prediction_was_elevated(patient.id, DiseaseType.STROKE, current.id) is False


def test_previous_prediction_was_elevated_ignores_current_prediction(db_session):
    """Only the MOST RECENT prior prediction counts — the current one and
    older ones are not considered."""
    patient = _make_patient(db_session)
    older = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.HIGH)
    mid = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.LOW)
    current = _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.CRITICAL)
    svc = _service(db_session)
    # mid is the most recent prior -> low, so NOT elevated, despite older being high.
    assert svc._previous_prediction_was_elevated(patient.id, DiseaseType.STROKE, current.id) is False
    # sanity: remove the low mid prediction -> older high becomes the most recent prior.
    db_session.delete(mid)
    db_session.commit()
    assert svc._previous_prediction_was_elevated(patient.id, DiseaseType.STROKE, current.id) is True


def test_previous_prediction_was_elevated_only_considers_same_disease(db_session):
    """A high stroke prediction must not count as confirmation for
    hypertension — conditions are kept independent."""
    patient = _make_patient(db_session)
    _make_prediction(db_session, patient, DiseaseType.STROKE, RiskLevel.HIGH)
    current = _make_prediction(db_session, patient, DiseaseType.HYPERTENSION, RiskLevel.CRITICAL)
    svc = _service(db_session)
    assert svc._previous_prediction_was_elevated(patient.id, DiseaseType.HYPERTENSION, current.id) is False
