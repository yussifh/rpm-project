"""Tests for: admin-assigned primary condition, disease assessments, and
explainable-AI reasons on predictions.

Note: this used to also cover a doctor directly registering patients and
doctor-scoped assignment/visibility checks, but there is no doctor role
in this system anymore — primary_condition is assigned by admin, and
patients trigger their own predictions (see api/v1/predictions.py).
"""

from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers


def _get_patient_id(client, admin_token):
    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    return patients[0]["id"]


# --- Assign primary condition ---


def test_admin_can_assign_primary_condition(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.patch(
        f"/api/v1/patients/{patient_id}/condition",
        json={"primary_condition": "hypertension"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["primary_condition"] == "hypertension"


def test_patient_cannot_assign_own_condition(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.patch(
        f"/api/v1/patients/{patient_id}/condition",
        json={"primary_condition": "diabetes"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 403


# --- Disease assessments ---


def test_patient_can_submit_own_assessment(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/assessments",
        json={
            "disease_type": "hypertension",
            "symptoms": {"severe_headache": True, "chest_pain": False, "dizziness": True},
        },
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    assert resp.json()["symptoms"]["severe_headache"] is True

    listing = client.get(f"/api/v1/patients/{patient_id}/assessments", headers=auth_headers(admin_token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_other_patient_cannot_view_assessments(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.post(
        f"/api/v1/patients/{patient_id}/assessments",
        json={"disease_type": "diabetes", "symptoms": {"blurred_vision": True}},
        headers=auth_headers(patient_token),
    )

    other_payload = {
        "email": "other-assess@example.com",
        "password": "SecurePass123",
        "full_name": "Other Patient",
        "date_of_birth": "1991-02-02",
        "gender": "female",
    }
    client.post("/api/v1/admin/users/patient", json=other_payload, headers=auth_headers(admin_token))
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": other_payload["email"], "password": other_payload["password"]},
    )
    other_patient_token = login_resp.json()["access_token"]

    resp = client.get(f"/api/v1/patients/{patient_id}/assessments", headers=auth_headers(other_patient_token))
    assert resp.status_code == 403


# --- Explainable AI reasons ---


def test_prediction_includes_reasons(client, admin_token, patient_token, db_session):
    import uuid

    from app.models.vitals import VitalReading

    patient_id = _get_patient_id(client, admin_token)

    for i in range(3):
        db_session.add(
            VitalReading(
                patient_id=uuid.UUID(patient_id),
                blood_pressure_systolic=175,
                blood_pressure_diastolic=110,
                heart_rate_bpm=95,
                blood_glucose_mg_dl=110,
                recorded_at=datetime.now(timezone.utc) - timedelta(hours=i),
            )
        )
    db_session.commit()

    client.patch(
        "/api/v1/patients/me",
        json={"height_cm": 175, "weight_kg": 80},
        headers=auth_headers(patient_token),
    )

    resp = client.post(
        f"/api/v1/patients/{patient_id}/predictions/hypertension",
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "reasons" in body
    assert isinstance(body["reasons"], list)
    assert len(body["reasons"]) > 0
    assert any("blood pressure" in r.lower() for r in body["reasons"])
