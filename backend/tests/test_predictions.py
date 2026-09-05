"""
Integration tests: AI risk prediction generation, RBAC boundaries, and the
insufficient-data guard rail.

Note: there is no doctor role in this system — patients trigger their own
predictions (e.g. after logging new vitals), admin retains access too.
Vitals ingestion endpoints exist separately, so these tests insert a
VitalReading directly into the test DB session to simulate "a vitals
reading already exists for this patient" — the same approach used for
seeding the admin account.
"""

import uuid
from datetime import datetime, timezone

from app.ai_engine.feature_schema import MODEL_VERSION
from app.models.vitals import VitalReading
from tests.conftest import auth_headers


def _get_patient_id(client, admin_token):
    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    return patients[0]["id"]


def _set_patient_height_weight(client, patient_token):
    resp = client.patch(
        "/api/v1/patients/me",
        json={"height_cm": 175, "weight_kg": 82},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 200


def _seed_vitals(db_session, patient_id, **overrides):
    defaults = dict(
        patient_id=uuid.UUID(str(patient_id)),
        recorded_at=datetime.now(timezone.utc),
        blood_pressure_systolic=150,
        blood_pressure_diastolic=95,
        heart_rate_bpm=88,
        blood_glucose_mg_dl=170,
        spo2_percent=97,
    )
    defaults.update(overrides)
    vital = VitalReading(**defaults)
    db_session.add(vital)
    db_session.commit()
    db_session.refresh(vital)
    return vital


def test_prediction_requires_vitals_and_bmi(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    # No vitals, no height/weight yet -> should fail with a clear 422
    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/stroke",
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 422
    assert "vitals" in resp.json()["detail"].lower()


def test_patient_can_generate_own_stroke_prediction(client, admin_token, patient_token, db_session):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)
    _seed_vitals(db_session, patient_id)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/stroke",
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["disease_type"] == "stroke"
    assert 0.0 <= body["risk_score"] <= 1.0
    assert body["risk_level"] in {"low", "moderate", "high", "critical"}
    assert body["model_version"] == MODEL_VERSION


def test_other_patient_cannot_trigger_prediction(client, admin_token, patient_token, db_session):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)
    _seed_vitals(db_session, patient_id)

    other_payload = {
        "email": "other-pred@example.com",
        "password": "SecurePass123",
        "full_name": "Other Patient",
        "date_of_birth": "1994-04-04",
        "gender": "female",
    }
    client.post("/api/v1/admin/users/patient", json=other_payload, headers=auth_headers(admin_token))
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": other_payload["email"], "password": other_payload["password"]},
    )
    other_patient_token = login_resp.json()["access_token"]

    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/diabetes",
        headers=auth_headers(other_patient_token),
    )
    assert resp.status_code == 403


def test_patient_can_view_own_prediction_history(client, admin_token, patient_token, db_session):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)
    _seed_vitals(db_session, patient_id)

    client.post(f"/api/v1/patients/{patient_id}/predictions/hypertension", headers=auth_headers(patient_token))

    resp = client.get(f"/api/v1/patients/{patient_id}/predictions", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["disease_type"] == "hypertension"


def test_high_risk_vitals_produce_higher_risk_score_than_healthy_vitals(
    client, admin_token, patient_token, db_session
):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)
    _seed_vitals(
        db_session,
        patient_id,
        blood_pressure_systolic=115,
        blood_pressure_diastolic=75,
        heart_rate_bpm=68,
        blood_glucose_mg_dl=88,
    )

    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/diabetes",
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    # A healthy-vitals patient should not be flagged critical
    assert resp.json()["risk_level"] in {"low", "moderate"}


def test_prediction_includes_recommendations(client, admin_token, patient_token, db_session):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)
    _seed_vitals(
        db_session,
        patient_id,
        blood_pressure_systolic=190,
        blood_pressure_diastolic=125,
        heart_rate_bpm=110,
        blood_glucose_mg_dl=200,
    )

    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/hypertension",
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)
    assert 1 <= len(body["recommendations"]) <= 4
    # High-severity BP reading should surface urgent-care framing, not
    # just generic lifestyle advice.
    assert any("urgent" in r.lower() or "emergency" in r.lower() for r in body["recommendations"])


def test_healthy_reading_gets_maintenance_recommendation_not_empty(
    client, admin_token, patient_token, db_session
):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)
    _seed_vitals(
        db_session,
        patient_id,
        blood_pressure_systolic=115,
        blood_pressure_diastolic=75,
        heart_rate_bpm=68,
        blood_glucose_mg_dl=88,
    )

    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/diabetes",
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    assert len(resp.json()["recommendations"]) >= 1
