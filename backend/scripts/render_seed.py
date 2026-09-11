"""
Render deploy-time seeder.

Creates (idempotently) the full schema plus a working demo dataset so the
deployed PWA is usable immediately on a phone:

  - admin account         admin@rpm.com      / AdminPass123
  - demo patient          hamza@rpm.com      / PatientPass123
  - Yussif Hamza          male, 1970-03-14, 170cm/74kg, primary condition = stroke
  - 18-staged vitals history (LOW -> MODERATE -> HIGH -> CRITICAL -> RECOVERY)
    generated through the REAL VitalsService.record_reading pipeline, so
    predictions/alerts/notifications are identical to a local demo.

Runs schema creation with create_all() (schema = current ORM models) rather
than alembic, so a fresh deploy always matches the code that is running.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from datetime import date, timedelta, timezone
from datetime import datetime

import app.models  # noqa: F401  (import side-effect: registers all tables)

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.enums import DiseaseType, Gender, UserRole, VitalSource
from app.models.user import User
from app.models.patient import PatientProfile
from app.models.admin import AdminProfile
from app.models.prediction import RiskPrediction
from app.models.vitals import VitalReading
from app.schemas.vitals import VitalReadingCreate
from app.services.vitals_service import VitalsService

# small standalone copy of the demo READINGS so this script depends only on
# the app package, not on the local reset_seed_demo_history module.
STROKE, DIABETES, HYPERTENSION = DiseaseType.STROKE, DiseaseType.DIABETES, DiseaseType.HYPERTENSION
CONDITIONS = [DIABETES, HYPERTENSION, STROKE]

# (days_ago, sys, dia, hr, glucose, pedigree, bmi, spo2, temp, rr, weight, note)
DEMO_READINGS = [
    (56, 112, 74, 60, 100.0, 0.28, 24.4, 98.0, 36.3, 15, 70.5, "Routine check-in, feeling well."),
    (53, 114, 75, 62, 104.0, 0.30, 24.5, 98.0, 36.4, 15, 70.8, "Baseline vitals normal."),
    (50, 116, 76, 63, 108.0, 0.32, 24.6, 98.0, 36.4, 15, 71.0, "No complaints."),
    (46, 128, 81, 68, 128.0, 0.42, 25.2, 97.0, 36.5, 16, 72.6, "Slightly elevated glucose after heavy meal."),
    (42, 130, 82, 69, 133.0, 0.45, 25.4, 97.0, 36.5, 16, 73.0, "Watching diet, fewer sweets."),
    (38, 132, 84, 71, 138.0, 0.48, 25.6, 97.0, 36.6, 16, 73.5, "Blood pressure starting to trend up."),
    (34, 135, 85, 72, 142.0, 0.50, 25.8, 96.0, 36.6, 16, 73.9, "Pre-hypertensive range noted."),
    (30, 138, 88, 74, 146.0, 0.55, 26.0, 96.0, 36.7, 17, 74.4, "Moderate risk, lifestyle counselling started."),
    (26, 148, 92, 78, 188.0, 0.65, 26.4, 95.0, 36.8, 17, 75.4, "Consistently elevated pressure and glucose."),
    (22, 150, 93, 79, 192.0, 0.67, 26.5, 95.0, 36.8, 17, 75.8, "High risk, medication review suggested."),
    (18, 152, 94, 80, 196.0, 0.68, 26.6, 95.0, 36.9, 18, 76.1, "Marked worsening since last check-in."),
    (14, 156, 96, 82, 204.0, 0.70, 26.8, 94.0, 36.9, 18, 76.7, "Uncontrolled readings, advised to seek care."),
    (10, 172, 106, 90, 242.0, 0.84, 27.4, 93.0, 37.1, 19, 78.0, "CRITICAL — hospital review advised."),
    (9,  176, 108, 92, 250.0, 0.86, 27.5, 92.0, 37.2, 19, 78.3, "CRITICAL sustained — emergency protocol."),
    (8,  150, 94, 80, 178.0, 0.68, 26.9, 95.0, 37.0, 18, 76.9, "Post-clinic review, treatment started."),
    (6,  142, 89, 75, 155.0, 0.60, 26.4, 96.0, 36.9, 17, 75.9, "Improving on medication."),
    (4,  138, 87, 73, 148.0, 0.55, 26.1, 96.0, 36.8, 17, 75.3, "Better control, staying on plan."),
    (2,  134, 85, 71, 142.0, 0.52, 25.9, 97.0, 36.7, 16, 74.8, "Stable — moderate risk, monitoring continues."),
]


def _ensure_user(db, email, password, full_name, role):
    user = db.query(User).filter(User.email == email.lower()).first()
    if user:
        return user
    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_verified=True,
    )
    db.add(user)
    # Flush each UUID-backed User individually. SQLAlchemy's Postgres
    # insertmanyvalues path can otherwise fail to correlate UUID sentinel
    # values when multiple new users are flushed in the same batch.
    db.flush()
    return user


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = _ensure_user(db, "admin@rpm.com", "AdminPass123", "System Admin", UserRole.ADMIN)
        if not admin.admin_profile:
            db.add(AdminProfile(user=admin, department="IT", job_title="System Admin", is_super_admin=True))
            db.flush()

        patient = _ensure_user(db, "hamza@rpm.com", "PatientPass123", "Yussif Hamza", UserRole.PATIENT)
        if not patient.patient_profile:
            db.add(PatientProfile(
                user=patient,
                date_of_birth=date(1970, 3, 14),
                gender=Gender.MALE,
                height_cm=170.0,
                weight_kg=74.0,
                primary_condition=DiseaseType.STROKE,
            ))
            db.flush()
        db.commit()
        db.refresh(admin)
        db.refresh(patient)

        profile = patient.patient_profile
        existing = db.query(VitalReading).filter(VitalReading.patient_id == profile.id).count()
        if existing:
            print(f"vitals: {existing} readings already present — no reseed")
            print(f"predictions: {db.query(RiskPrediction).count()}")
            return

        svc = VitalsService(db)
        now = datetime.now(timezone.utc)
        for (days_ago, sys_, dia, hr, glu, ped, bmi, spo2, temp, rr, weight, note) in DEMO_READINGS:
            svc.record_reading(
                profile.id,
                VitalReadingCreate(
                    recorded_at=now - timedelta(days=days_ago),
                    source=VitalSource.MANUAL,
                    conditions=CONDITIONS,
                    blood_pressure_systolic=sys_,
                    blood_pressure_diastolic=dia,
                    heart_rate_bpm=hr,
                    blood_glucose_mg_dl=glu,
                    diabetes_pedigree_function=ped,
                    bmi=bmi,
                    spo2_percent=spo2,
                    temperature_celsius=temp,
                    respiratory_rate=rr,
                    weight_kg=weight,
                    notes=note,
                ),
            )
        db.commit()
        print(f"seeded {len(DEMO_READINGS)} readings")
        print(f"predictions: {db.query(RiskPrediction).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
