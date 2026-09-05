"""
Auth flow tests: patient onboarding (admin-only, no public
self-registration), login, protected route access, RBAC, token refresh,
and logout/revocation.
"""

from tests.conftest import auth_headers

VALID_PATIENT_PAYLOAD = {
    "email": "jane.doe@example.com",
    "password": "SecurePass123",
    "full_name": "Jane Doe",
    "phone_number": "+15551234567",
    "date_of_birth": "1990-05-14",
    "gender": "female",
    "blood_group": "O+",
}


def _create_patient_as_admin(client, admin_token, payload=VALID_PATIENT_PAYLOAD):
    return client.post("/api/v1/admin/users/patient", json=payload, headers=auth_headers(admin_token))


def test_public_self_registration_endpoint_does_not_exist(client):
    """There is deliberately no public /auth/register — every patient is
    onboarded by an admin, matching the workflow where a patient can't
    self-assign into the monitoring system."""
    response = client.post("/api/v1/auth/register", json=VALID_PATIENT_PAYLOAD)
    assert response.status_code == 404


def test_admin_can_create_patient_account(client, admin_token):
    response = _create_patient_as_admin(client, admin_token)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "jane.doe@example.com"
    assert body["role"] == "patient"
    assert "hashed_password" not in body  # never leak the hash


def test_duplicate_email_rejected(client, admin_token):
    _create_patient_as_admin(client, admin_token)
    response = _create_patient_as_admin(client, admin_token)
    assert response.status_code == 409


def test_weak_password_rejected(client, admin_token):
    payload = {**VALID_PATIENT_PAYLOAD, "email": "weak@example.com", "password": "alllettersnodigits"}
    response = _create_patient_as_admin(client, admin_token, payload)
    assert response.status_code == 422


def test_login_success_returns_tokens(client, admin_token):
    _create_patient_as_admin(client, admin_token)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": VALID_PATIENT_PAYLOAD["email"], "password": VALID_PATIENT_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(client, admin_token):
    _create_patient_as_admin(client, admin_token)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": VALID_PATIENT_PAYLOAD["email"], "password": "WrongPassword123"},
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, admin_token):
    _create_patient_as_admin(client, admin_token)
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": VALID_PATIENT_PAYLOAD["email"], "password": VALID_PATIENT_PAYLOAD["password"]},
    )
    access_token = login_resp.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == VALID_PATIENT_PAYLOAD["email"]


def test_refresh_token_issues_new_access_token(client, admin_token):
    _create_patient_as_admin(client, admin_token)
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": VALID_PATIENT_PAYLOAD["email"], "password": VALID_PATIENT_PAYLOAD["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", params={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_revokes_refresh_token(client, admin_token):
    _create_patient_as_admin(client, admin_token)
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": VALID_PATIENT_PAYLOAD["email"], "password": VALID_PATIENT_PAYLOAD["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = client.post("/api/v1/auth/logout", params={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    # The same refresh token must now be rejected
    reuse_resp = client.post("/api/v1/auth/refresh", params={"refresh_token": refresh_token})
    assert reuse_resp.status_code == 401
