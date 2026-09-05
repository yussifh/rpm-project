"""Tests for admin-editable patient and user account details.

Note: this used to also cover doctor profile editing, but there is no
doctor role in this system anymore.
"""

from tests.conftest import auth_headers


def _get_patient_id(client, admin_token):
    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    return patients[0]["id"]


def test_admin_can_edit_patient_profile(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.patch(
        f"/api/v1/admin/patients/{patient_id}",
        json={"blood_group": "O+", "height_cm": 170, "weight_kg": 68},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["blood_group"] == "O+"
    assert body["height_cm"] == 170


def test_admin_can_edit_user_identity_fields(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    patient_user_id = client.get(f"/api/v1/patients/{patient_id}", headers=auth_headers(admin_token)).json()["user_id"]

    resp = client.patch(
        f"/api/v1/admin/users/{patient_user_id}",
        json={"full_name": "Updated Name", "phone_number": "+15550001111"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Updated Name"
    assert body["phone_number"] == "+15550001111"


def test_admin_cannot_edit_email_to_existing_email(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    patient_user_id = client.get(f"/api/v1/patients/{patient_id}", headers=auth_headers(admin_token)).json()["user_id"]

    resp = client.patch(
        f"/api/v1/admin/users/{patient_user_id}",
        json={"email": "admin@example.com"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409


def test_non_admin_cannot_edit_patient_profile(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.patch(
        f"/api/v1/admin/patients/{patient_id}",
        json={"blood_group": "Hacked"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 403


def test_edit_nonexistent_patient_returns_404(client, admin_token):
    resp = client.patch(
        "/api/v1/admin/patients/00000000-0000-0000-0000-000000000000",
        json={"blood_group": "O+"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404
