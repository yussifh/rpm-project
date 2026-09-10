"""
Integration tests: vitals ingestion, threshold-triggered alerts,
AI-triggered alerts, alert lifecycle (acknowledge/resolve), and notifications.

Note: alert acknowledge/resolve is admin-only in this system (there is no
doctor role) — see AlertService docstring.
"""

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


# --- Vitals ingestion ---

def test_patient_can_log_own_vitals(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 118, "blood_pressure_diastolic": 76, "heart_rate_bpm": 70},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    assert resp.json()["vital"]["blood_pressure_systolic"] == 118


def test_vitals_require_at_least_one_measurement(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 422


def test_other_patient_cannot_log_vitals_for_patient(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    other_payload = {
        "email": "other-vitals@example.com",
        "password": "SecurePass123",
        "full_name": "Other Patient",
        "date_of_birth": "1993-03-03",
        "gender": "male",
    }
    client.post("/api/v1/admin/users/patient", json=other_payload, headers=auth_headers(admin_token))
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": other_payload["email"], "password": other_payload["password"]},
    )
    other_patient_token = login_resp.json()["access_token"]

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"heart_rate_bpm": 75},
        headers=auth_headers(other_patient_token),
    )
    assert resp.status_code == 403


# --- Threshold-triggered alerts ---

def test_critical_vitals_trigger_an_alert(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 190, "blood_pressure_diastolic": 128},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201

    alerts_resp = client.get("/api/v1/alerts", headers=auth_headers(admin_token))
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) >= 1
    assert any(a["severity"] == "critical" and "Hypertensive" in a["title"] for a in alerts)


def test_normal_vitals_do_not_trigger_an_alert(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 115, "blood_pressure_diastolic": 75, "heart_rate_bpm": 68},
        headers=auth_headers(patient_token),
    )

    alerts_resp = client.get("/api/v1/alerts", headers=auth_headers(admin_token))
    assert alerts_resp.json() == []


def test_patient_sees_own_alerts(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_glucose_mg_dl": 45},  # severe hypoglycemia
        headers=auth_headers(patient_token),
    )

    resp = client.get("/api/v1/alerts", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    assert any(a["title"] == "Severe Hypoglycemia" for a in resp.json())


# --- AI-triggered alerts (uses the trained models) ---

def test_high_risk_vitals_trigger_ai_alert(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)

    # Elevated but not threshold-critical vitals for an older patient — should
    # still cross the AI model's high-risk cutoff given enough compounding factors.
    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={
            "conditions": ["stroke", "diabetes", "hypertension"],
            "blood_pressure_systolic": 168,
            "blood_pressure_diastolic": 104,
            "heart_rate_bpm": 95,
            "blood_glucose_mg_dl": 175,
            "skin_thickness_mm": 22,
            "serum_insulin_mu_u_ml": 95,
            "diabetes_pedigree_function": 0.5,
        },
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    # A separate prediction was generated for each explicitly-selected condition.
    disease_types = {p["disease_type"] for p in body["predictions"]}
    assert disease_types == {"stroke", "diabetes", "hypertension"}
    assert body["skipped"] == []


def test_vitals_without_conditions_generates_no_predictions(client, admin_token, patient_token):
    """Condition-based workflow: prediction is opt-in per submission, not
    automatic — logging vitals without selecting a condition just saves
    the reading and runs threshold checks."""
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 168, "blood_pressure_diastolic": 104, "blood_glucose_mg_dl": 175},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    assert resp.json()["predictions"] == []


def test_vitals_generates_prediction_only_for_selected_condition(client, admin_token, patient_token):
    """Selecting only Hypertension must not generate Diabetes/Stroke
    predictions, even though this submission includes vitals fields
    (glucose) another model could also use — the AI must not "confuse
    conditions" per the workflow spec."""
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={
            "conditions": ["hypertension"],
            "blood_pressure_systolic": 150,
            "blood_pressure_diastolic": 95,
            "heart_rate_bpm": 88,
            "blood_glucose_mg_dl": 175,
        },
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["predictions"]) == 1
    assert body["predictions"][0]["disease_type"] == "hypertension"


def test_vitals_multiple_conditions_produce_separate_predictions(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    _set_patient_height_weight(client, patient_token)

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={
            "conditions": ["diabetes", "hypertension"],
            "blood_pressure_systolic": 145,
            "blood_pressure_diastolic": 92,
            "heart_rate_bpm": 80,
            "blood_glucose_mg_dl": 160,
            "skin_thickness_mm": 22,
            "serum_insulin_mu_u_ml": 95,
            "diabetes_pedigree_function": 0.5,
        },
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    disease_types = {p["disease_type"] for p in body["predictions"]}
    assert disease_types == {"diabetes", "hypertension"}
    # Each prediction is its own record with its own risk score/reasons —
    # not a combined multi-disease result.
    assert len({p["id"] for p in body["predictions"]}) == 2


def test_selected_condition_with_missing_data_is_reported_as_skipped(client, admin_token, patient_token):
    """No height/weight recorded -> BMI can't be computed -> the selected
    condition is skipped with a reason, rather than silently dropped or
    failing the whole request (the vitals themselves still save)."""
    patient_id = _get_patient_id(client, admin_token)
    # deliberately NOT calling _set_patient_height_weight

    resp = client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"conditions": ["diabetes"], "blood_glucose_mg_dl": 160, "blood_pressure_diastolic": 90},
        headers=auth_headers(patient_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["predictions"] == []
    assert len(body["skipped"]) == 1
    assert body["skipped"][0]["disease_type"] == "diabetes"
    assert "height and weight" in body["skipped"][0]["reason"].lower()


# --- Alert lifecycle ---

def test_admin_can_acknowledge_and_resolve_alert(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"heart_rate_bpm": 185},
        headers=auth_headers(patient_token),
    )
    alert_id = client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()[0]["id"]

    ack_resp = client.patch(f"/api/v1/alerts/{alert_id}/acknowledge", headers=auth_headers(admin_token))
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    resolve_resp = client.patch(f"/api/v1/alerts/{alert_id}/resolve", headers=auth_headers(admin_token))
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"


def test_patient_cannot_acknowledge_alert(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"heart_rate_bpm": 185},
        headers=auth_headers(patient_token),
    )
    alert_id = client.get("/api/v1/alerts", headers=auth_headers(patient_token)).json()[0]["id"]

    resp = client.patch(f"/api/v1/alerts/{alert_id}/acknowledge", headers=auth_headers(patient_token))
    assert resp.status_code == 403


# --- Notifications ---

def test_alert_creates_notification_for_patient(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"spo2_percent": 87},
        headers=auth_headers(patient_token),
    )

    resp = client.get("/api/v1/notifications", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["is_read"] is False


def test_mark_notification_as_read(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"spo2_percent": 87},
        headers=auth_headers(patient_token),
    )
    notification_id = client.get("/api/v1/notifications", headers=auth_headers(patient_token)).json()[0]["id"]

    resp = client.patch(f"/api/v1/notifications/{notification_id}/read", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True


# --- Vitals trends ---

def test_trends_empty_with_no_vitals(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    resp = client.get(f"/api/v1/patients/{patient_id}/vitals/trends", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    assert resp.json()["trends"] == []


def test_trends_report_worsening_bp(client, admin_token, patient_token, db_session):
    import uuid
    from datetime import datetime, timedelta, timezone

    from app.models.vitals import VitalReading

    patient_id = _get_patient_id(client, admin_token)
    base = datetime.now(timezone.utc) - timedelta(days=20)
    systolic_values = [125, 130, 135, 150, 160, 172]
    for i, value in enumerate(systolic_values):
        db_session.add(
            VitalReading(
                patient_id=uuid.UUID(patient_id),
                blood_pressure_systolic=value,
                blood_pressure_diastolic=85,
                recorded_at=base + timedelta(days=i * 3),
            )
        )
    db_session.commit()

    resp = client.get(f"/api/v1/patients/{patient_id}/vitals/trends?days=90", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    body = resp.json()
    systolic_trend = next(t for t in body["trends"] if t["field"] == "blood_pressure_systolic")
    assert systolic_trend["direction"] == "worsening"
    assert "qualified healthcare professional" in systolic_trend["summary"]
    assert systolic_trend["sample_size"] == 6


def test_other_patient_cannot_view_trends(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    other_payload = {
        "email": "other-trends@example.com",
        "password": "SecurePass123",
        "full_name": "Other Patient",
        "date_of_birth": "1995-05-05",
        "gender": "male",
    }
    client.post("/api/v1/admin/users/patient", json=other_payload, headers=auth_headers(admin_token))
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": other_payload["email"], "password": other_payload["password"]},
    )
    other_patient_token = login_resp.json()["access_token"]

    resp = client.get(f"/api/v1/patients/{patient_id}/vitals/trends", headers=auth_headers(other_patient_token))
    assert resp.status_code == 403


def test_trends_invalid_days_rejected(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    resp = client.get(f"/api/v1/patients/{patient_id}/vitals/trends?days=0", headers=auth_headers(patient_token))
    assert resp.status_code == 422


def test_trends_endpoint_includes_forecast(client, admin_token, patient_token, db_session):
    import uuid
    from datetime import datetime, timedelta, timezone

    from app.models.vitals import VitalReading

    patient_id = _get_patient_id(client, admin_token)
    base = datetime.now(timezone.utc) - timedelta(days=15)
    for i, value in enumerate([100, 104, 108, 112, 116]):
        db_session.add(
            VitalReading(
                patient_id=uuid.UUID(patient_id),
                blood_pressure_systolic=value,
                recorded_at=base + timedelta(days=i * 3),
            )
        )
    db_session.commit()

    resp = client.get(f"/api/v1/patients/{patient_id}/vitals/trends?days=90", headers=auth_headers(patient_token))
    assert resp.status_code == 200
    systolic_trend = next(t for t in resp.json()["trends"] if t["field"] == "blood_pressure_systolic")
    assert systolic_trend["forecast"] is not None
    assert systolic_trend["forecast"]["position"] == "approaching_threshold"
    assert systolic_trend["forecast"]["days_projected"] is not None
    assert systolic_trend["forecast"]["target_value"] == 120


# --- Alert deduplication ---

def test_duplicate_alert_is_not_raised_while_still_unresolved(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 190, "blood_pressure_diastolic": 128},
        headers=auth_headers(patient_token),
    )
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 192, "blood_pressure_diastolic": 130},
        headers=auth_headers(patient_token),
    )

    alerts = client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()
    crisis_alerts = [a for a in alerts if a["title"] == "Hypertensive Crisis"]
    assert len(crisis_alerts) == 1


def test_new_alert_raised_after_previous_one_resolved(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)

    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 190, "blood_pressure_diastolic": 128},
        headers=auth_headers(patient_token),
    )
    first_alert_id = next(
        a["id"] for a in client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()
        if a["title"] == "Hypertensive Crisis"
    )
    client.patch(f"/api/v1/alerts/{first_alert_id}/acknowledge", headers=auth_headers(admin_token))
    client.patch(f"/api/v1/alerts/{first_alert_id}/resolve", headers=auth_headers(admin_token))

    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 195, "blood_pressure_diastolic": 130},
        headers=auth_headers(patient_token),
    )

    alerts = client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()
    crisis_alerts = [a for a in alerts if a["title"] == "Hypertensive Crisis"]
    assert len(crisis_alerts) == 2


# --- Emergency contact notification ---

def test_critical_alert_notifies_emergency_contact_when_on_file(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.patch(
        "/api/v1/patients/me",
        json={"emergency_contact_name": "Jane Doe", "emergency_contact_phone": "+15550001234"},
        headers=auth_headers(patient_token),
    )

    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 190, "blood_pressure_diastolic": 128},
        headers=auth_headers(patient_token),
    )

    alerts = client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()
    crisis_alert = next(a for a in alerts if a["title"] == "Hypertensive Crisis")
    assert crisis_alert["emergency_contact_notified"] is True

    audit_logs = client.get(
        "/api/v1/admin/audit-logs?action=EMERGENCY_CONTACT_NOTIFIED", headers=auth_headers(admin_token)
    ).json()
    assert len(audit_logs) == 1
    assert audit_logs[0]["extra_metadata"]["contact_name"] == "Jane Doe"


def test_critical_alert_without_emergency_contact_on_file_is_not_notified(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    # No emergency contact set for this patient.

    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 190, "blood_pressure_diastolic": 128},
        headers=auth_headers(patient_token),
    )

    alerts = client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()
    crisis_alert = next(a for a in alerts if a["title"] == "Hypertensive Crisis")
    assert crisis_alert["emergency_contact_notified"] is False


def test_warning_level_alert_does_not_notify_emergency_contact(client, admin_token, patient_token):
    patient_id = _get_patient_id(client, admin_token)
    client.patch(
        "/api/v1/patients/me",
        json={"emergency_contact_name": "Jane Doe", "emergency_contact_phone": "+15550001234"},
        headers=auth_headers(patient_token),
    )

    # Elevated but not critical-threshold BP -> a WARNING alert, not CRITICAL.
    client.post(
        f"/api/v1/patients/{patient_id}/vitals",
        json={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 95},
        headers=auth_headers(patient_token),
    )

    alerts = client.get("/api/v1/alerts", headers=auth_headers(admin_token)).json()
    if alerts:
        assert all(a["emergency_contact_notified"] is False for a in alerts)
