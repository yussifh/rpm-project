"""
One-time backfill: create alerts for existing HIGH/CRITICAL risk
predictions that were generated outside the normal record_reading
pipeline (so the alert pipeline never ran).

Creates one alert per disease type per patient, with severity based
on whether multiple critical predictions exist (sustained pattern).

Usage:
    cd backend && python -m scripts.backfill_alerts
"""
from collections import defaultdict

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.enums import AlertSeverity, RiskLevel
from app.models.notification import Notification
from app.models.patient import PatientProfile
from app.models.prediction import RiskPrediction
from app.repositories.alert_repository import AlertRepository


def main() -> None:
    db = SessionLocal()
    alerts_repo = AlertRepository(db)

    preds = list(
        db.execute(
            select(RiskPrediction).where(
                RiskPrediction.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
            )
        ).scalars().all()
    )

    if not preds:
        print("No HIGH/CRITICAL predictions found. Nothing to do.")
        return

    print(f"Found {len(preds)} HIGH/CRITICAL predictions.")

    groups: dict[tuple, list[RiskPrediction]] = defaultdict(list)
    for p in sorted(preds, key=lambda x: x.predicted_at):
        groups[(p.patient_id, p.disease_type)].append(p)

    created = 0
    skipped = 0

    for (patient_id, disease_type), predictions in groups.items():
        title = f"Elevated {disease_type.value.title()} Risk Detected"

        existing = alerts_repo.find_active_by_title(patient_id, title)
        if existing:
            print(f"  SKIP {title} (patient {patient_id}) - already exists")
            skipped += 1
            continue

        critical_count = sum(1 for p in predictions if p.risk_level == RiskLevel.CRITICAL)
        severity = AlertSeverity.CRITICAL if critical_count >= 2 else AlertSeverity.WARNING

        latest = predictions[-1]
        message = (
            f"AI model flagged {disease_type.value} risk as {latest.risk_level.value} "
            f"(score {latest.risk_score:.2f}). "
            f"{critical_count} critical prediction(s) recorded across {len(predictions)} total."
        )

        alert = Alert(
            patient_id=patient_id,
            severity=severity,
            title=title,
            message=message,
            related_prediction_id=latest.id,
        )
        alerts_repo.create(alert)
        print(f"  CREATED alert: {title} | severity={severity.value} (patient {patient_id})")
        created += 1

        patient = db.get(PatientProfile, patient_id)
        if patient and patient.user_id:
            notif = Notification(
                user_id=patient.user_id,
                title=title,
                message=message,
                notification_type="alert",
            )
            db.add(notif)
            db.commit()

    print(f"\nDone. Created {created} alerts, skipped {skipped} (already existed).")
    db.close()


if __name__ == "__main__":
    main()
