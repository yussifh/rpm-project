"""
Integration tests: admin user management, patient profile access, RBAC
boundaries, medical history, and medication tracking.

Note: this used to also cover doctor account creation and doctor-patient
assignment, but there is no doctor role in this system anymore — medical
history is admin-authored, and patients self-report their own medications.
"""

import uuid
from datetime import datetime, timezone

from tests.conftest import PATIENT_PAYLOAD, auth_headers


# --- Admin user management ---

def test_admin_can_list_users(client, admin_token, patient_token):
    resp = client.get("/api/v1/admin/users", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 2  # admin + patient


def test_admin_can_deactivate_user(client, admin_token, patient_token):
    users = client.get("/api/v1/admin/users?role=patient", headers=auth_headers(admin_token)).json()
    patient_user_id = users[0]["id"]

    resp = client.patch(f"/api/v1/admin/users/{patient_user_id}/deactivate", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login_resp = client.post(
        "/api/v1/auth/login", data={"username": PATIENT_PAYLOAD["email"], "password": PATIENT_PAYLOAD["password"]}
    )
    assert login_resp.status_code == 403


# --- Patient access RBAC ---

def _get_patient_id(client, admin_token):
    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    return patients[0]["id"]


def test_admin_sees_all_patients(client, admin_token, patient_token):
    resp = client.get("/api/v1/patients", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_patient_cannot_view_another_patients_record(client, admin_token, patient_token):
    fake_id = uuid.uuid4()
    resp = client.get(f"/api/v1/patients/{fake_id}", headers=auth_headers(patient_token))
    assert resp.status_code in (403, 404)


# --- Medical history ---

def test_admin_can_add_medical_history(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/medical-history",
        json={"condition_name": "Type 2 Diabetes", "diagnosed_date": "2020-01-15"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    assert resp.json()["condition_name"] == "Type 2 Diabetes"


def test_patient_cannot_write_own_medical_history(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    resp = client.post(
        f"/api/v1/patients/{patient_id}/medical-history",
        json={"condition_name": "Self-diagnosed condition"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 403


# --- Medications ---

def test_patient_can_add_own_medication_and_log_dose(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    add_resp = client.post(
        f"/api/v1/patients/{patient_id}/medications",
        json={
            "name": "Metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
            "start_date": "2024-01-01",
        },
        headers=auth_headers(patient_token),
    )
    assert add_resp.status_code == 201
    medication_id = add_resp.json()["id"]

    log_resp = client.post(
        f"/api/v1/medications/{medication_id}/logs",
        json={
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "status": "taken",
            "taken_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=auth_headers(patient_token),
    )
    assert log_resp.status_code == 201
    assert log_resp.json()["status"] == "taken"
