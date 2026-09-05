"""
Integration tests: audit log visibility and PDF report generation.

Note: this used to also cover appointment scheduling/conflict/cancel, but
there is no doctor role in this system anymore, and appointments only
made sense as a patient<->doctor concept — so that feature was removed
rather than refactored.
"""

from tests.conftest import auth_headers


def _get_patient_id(client, admin_token):
    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    return patients[0]["id"]


# --- Audit logging ---


def test_admin_can_view_audit_logs_of_patient_creation(client, admin_token):
    client.post(
        "/api/v1/admin/users/patient",
        json={
            "email": "audited.patient@example.com",
            "password": "SecurePass123",
            "full_name": "Audited Patient",
            "date_of_birth": "1990-01-01",
            "gender": "female",
        },
        headers=auth_headers(admin_token),
    )

    resp = client.get("/api/v1/admin/audit-logs?action=CREATE_PATIENT", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "CREATE_PATIENT"
    assert logs[0]["extra_metadata"]["email"] == "audited.patient@example.com"


def test_non_admin_cannot_view_audit_logs(client, patient_token):
    resp = client.get("/api/v1/admin/audit-logs", headers=auth_headers(patient_token))
    assert resp.status_code == 403


def test_add_medication_is_audited(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    client.post(
        f"/api/v1/patients/{patient_id}/medications",
        json={"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily", "start_date": "2024-01-01"},
        headers=auth_headers(patient_token),
    )

    resp = client.get("/api/v1/admin/audit-logs", headers=auth_headers(admin_token))
    actions = {log["action"] for log in resp.json()}
    assert "ADD_MEDICATION" in actions


# --- Reports ---


def test_generate_patient_summary_report(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.get(f"/api/v1/patients/{patient_id}/reports/summary", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_patient_can_download_own_report(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.get(f"/api/v1/patients/{patient_id}/reports/summary", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_patient_cannot_download_other_patients_report(client, admin_token, patient_token):
    other_payload = {
        "email": "other.patient@example.com",
        "password": "SecurePass123",
        "full_name": "Other Patient",
        "date_of_birth": "1992-06-15",
        "gender": "male",
    }
    client.post("/api/v1/admin/users/patient", json=other_payload, headers=auth_headers(admin_token))
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": other_payload["email"], "password": other_payload["password"]},
    )
    other_patient_token = login_resp.json()["access_token"]

    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    original_patient_id = next(p["id"] for p in patients if p["email"] != other_payload["email"])

    resp = client.get(
        f"/api/v1/patients/{original_patient_id}/reports/summary", headers=auth_headers(other_patient_token)
    )
    assert resp.status_code == 403
