"""
Tests for: admin-created patient accounts and self-service password change.

Note: this used to also cover doctor-patient messaging threads, but there
is no doctor role in this system anymore — patient-facing "messaging" is
the AI Health Assistant (see Phase 3), not covered here.
"""

from tests.conftest import PATIENT_PAYLOAD, auth_headers

PATIENT_CREATE_PAYLOAD = {
    "email": "onboarded-patient@example.com",
    "password": "SecurePass123",
    "full_name": "Onboarded Patient",
    "date_of_birth": "1990-01-01",
    "gender": "female",
}


# --- Admin creates patient ---


def test_admin_can_create_patient(client, admin_token):
    resp = client.post("/api/v1/admin/users/patient", json=PATIENT_CREATE_PAYLOAD, headers=auth_headers(admin_token))
    assert resp.status_code == 201
    assert resp.json()["role"] == "patient"

    # the new patient can log in immediately (admin-created accounts are pre-verified)
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": PATIENT_CREATE_PAYLOAD["email"], "password": PATIENT_CREATE_PAYLOAD["password"]},
    )
    assert login_resp.status_code == 200


def test_non_admin_cannot_create_patient(client, patient_token):
    resp = client.post("/api/v1/admin/users/patient", json=PATIENT_CREATE_PAYLOAD, headers=auth_headers(patient_token))
    assert resp.status_code == 403


# --- Password change ---


def test_user_can_change_own_password(client, patient_token):
    resp = client.patch(
        "/api/v1/auth/me/password",
        json={"current_password": PATIENT_PAYLOAD["password"], "new_password": "NewSecurePass456"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 200

    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": PATIENT_PAYLOAD["email"], "password": "NewSecurePass456"},
    )
    assert login_resp.status_code == 200


def test_change_password_rejects_wrong_current_password(client, patient_token):
    resp = client.patch(
        "/api/v1/auth/me/password",
        json={"current_password": "WrongPassword123", "new_password": "NewSecurePass456"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 400
