"""
Integration tests for the AI Health Assistant chat.

Note: ANTHROPIC_API_KEY is unset in the test environment (no network
egress), so most tests exercise the paths that don't require an actual
LLM call: RBAC, message persistence, and the deterministic emergency
override (see AssistantService._has_active_emergency). One test patches
AssistantService._call_llm directly to exercise the "normal" reply path
without needing the real anthropic client installed.
"""

import uuid

from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertStatus
from app.services.assistant_service import AssistantService
from tests.conftest import auth_headers


def _get_patient_id(client, admin_token):
    patients = client.get("/api/v1/patients", headers=auth_headers(admin_token)).json()
    return patients[0]["id"]


def test_no_api_key_returns_503(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": "What does my blood pressure mean?"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 503

    # The patient's own message is still persisted even though the reply failed.
    history = client.get(f"/api/v1/patients/{patient_id}/assistant/messages", headers=auth_headers(patient_token))
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["role"] == "user"


def test_other_patient_cannot_send_message(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    other_payload = {
        "email": "other-assistant@example.com",
        "password": "SecurePass123",
        "full_name": "Other Patient",
        "date_of_birth": "1990-07-07",
        "gender": "female",
    }
    client.post("/api/v1/admin/users/patient", json=other_payload, headers=auth_headers(admin_token))
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": other_payload["email"], "password": other_payload["password"]},
    )
    other_patient_token = login_resp.json()["access_token"]

    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": "Show me their vitals"},
        headers=auth_headers(other_patient_token),
    )
    assert resp.status_code == 403


def test_empty_message_rejected(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": ""},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 422


def test_active_critical_alert_triggers_emergency_override(client, admin_token, patient_token, db_session):
    patient_id = _get_patient_id(client, admin_token)

    db_session.add(
        Alert(
            patient_id=uuid.UUID(patient_id),
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.NEW,
            title="Hypertensive Crisis",
            message="Blood pressure 195/125 mmHg requires immediate attention.",
        )
    )
    db_session.commit()

    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": "Am I okay?"},
        headers=auth_headers(patient_token),
    )
    # Emergency override bypasses the LLM entirely, so this succeeds even
    # with no API key configured.
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_emergency_override"] is True
    assert body["role"] == "assistant"
    assert "urgent attention" in body["content"] or "emergency" in body["content"].lower()


def test_resolved_critical_alert_does_not_trigger_override(client, admin_token, patient_token, db_session):
    patient_id = _get_patient_id(client, admin_token)

    db_session.add(
        Alert(
            patient_id=uuid.UUID(patient_id),
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.RESOLVED,
            title="Hypertensive Crisis",
            message="Resolved.",
        )
    )
    db_session.commit()

    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": "Am I okay?"},
        headers=auth_headers(patient_token),
    )
    # No active emergency, so this falls through to the LLM path, which
    # fails with 503 (no API key) rather than emergency-overriding.
    assert resp.status_code == 503


def test_acknowledged_but_unresolved_critical_alert_still_triggers_override(
    client, admin_token, patient_token, db_session
):
    patient_id = _get_patient_id(client, admin_token)

    db_session.add(
        Alert(
            patient_id=uuid.UUID(patient_id),
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACKNOWLEDGED,
            title="Hypertensive Crisis",
            message="Acknowledged but not yet resolved.",
        )
    )
    db_session.commit()

    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": "Am I okay?"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    assert resp.json()["is_emergency_override"] is True


def test_normal_reply_path_with_mocked_llm(client, admin_token, patient_token, db_session, monkeypatch):
    patient_id = _get_patient_id(client, admin_token)

    monkeypatch.setattr(
        AssistantService, "_call_llm", lambda self, context, history: "Your readings look within normal range."
    )

    resp = client.post(
        f"/api/v1/patients/{patient_id}/assistant/messages",
        json={"content": "How am I doing?"},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_emergency_override"] is False
    assert body["content"] == "Your readings look within normal range."

    history = client.get(f"/api/v1/patients/{patient_id}/assistant/messages", headers=auth_headers(patient_token))
    roles = [m["role"] for m in history.json()]
    assert roles == ["user", "assistant"]
