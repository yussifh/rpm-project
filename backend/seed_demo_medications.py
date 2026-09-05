import sys
sys.path.insert(0, ".")
import os
os.environ.setdefault("ENVIRONMENT", "development")

import random
import uuid
from datetime import datetime, timedelta, timezone, date

from app.db.session import SessionLocal
from app.models.patient import PatientProfile
from app.models.medication import Medication, MedicationLog
from app.models.enums import MedicationStatus

PATIENT_ID_STR = "af72b229-31eb-4189-9f76-d49d42d3601c"

# name, dosage, frequency, instructions, start_date offset(days from today)
PRESCRIPTIONS = [
    {
        "name": "Metformin",
        "dosage": "500mg",
        "frequency": "twice daily",
        "instructions": "Take with breakfast and dinner.",
        "start_offset_days": 90,
        "doses_per_day": 2,
        "dose_hours": [8, 20],
    },
    {
        "name": "Lisinopril",
        "dosage": "10mg",
        "frequency": "once daily",
        "instructions": "Take in the morning. Do not skip without consulting your clinician.",
        "start_offset_days": 120,
        "doses_per_day": 1,
        "dose_hours": [8],
    },
    {
        "name": "Atorvastatin",
        "dosage": "20mg",
        "frequency": "once daily",
        "instructions": "Take in the evening.",
        "start_offset_days": 120,
        "doses_per_day": 1,
        "dose_hours": [21],
    },
]


def _date_with_tz(d: date, hour: int) -> datetime:
    return datetime.combine(d, datetime.min.time().replace(hour=hour), tzinfo=timezone.utc)


def main():
    db = SessionLocal()
    patient = db.query(PatientProfile).filter_by(id=uuid.UUID(PATIENT_ID_STR)).first()
    if not patient:
        print("Patient not found")
        sys.exit(1)

    # Clear existing medications (cascades to medication_logs)
    db.query(Medication).filter(Medication.patient_id == patient.id).delete(synchronize_session=False)
    db.commit()

    today = date.today()
    now = datetime.now(timezone.utc)
    log_count = 0
    rng = random.Random(42)

    for spec in PRESCRIPTIONS:
        start = today - timedelta(days=spec["start_offset_days"])
        med = Medication(
            patient_id=patient.id,
            name=spec["name"],
            dosage=spec["dosage"],
            frequency=spec["frequency"],
            instructions=spec["instructions"],
            start_date=start,
            end_date=None,
            is_active=True,
        )
        db.add(med)
        db.flush()

        # Build ~14 days of adherence logs, roughly 85% adherence, with a
        # couple of "missed" and one "skipped" for realism. Logs only up to
        # the present moment (no future doses).
        for day_offset in range(14, 0, -1):
            day = today - timedelta(days=day_offset)
            for hour in spec["dose_hours"]:
                scheduled = _date_with_tz(day, hour)
                if scheduled > now:
                    continue
                roll = rng.random()  # ~85% taken, ~10% missed, ~5% skipped
                if roll < 0.85:
                    status = MedicationStatus.TAKEN
                    taken_at = scheduled + timedelta(minutes=(med.id.int % 60))
                elif roll < 0.95:
                    status = MedicationStatus.MISSED
                    taken_at = None
                else:
                    status = MedicationStatus.SKIPPED
                    taken_at = None
                db.add(
                    MedicationLog(
                        medication_id=med.id,
                        scheduled_at=scheduled,
                        status=status,
                        taken_at=taken_at,
                    )
                )
                log_count += 1

        print(f"  {spec['name']} {spec['dosage']} ({spec['frequency']})")

    db.commit()
    db.close()
    print(f"Seeded {len(PRESCRIPTIONS)} medications with {log_count} adherence logs.")


if __name__ == "__main__":
    main()
