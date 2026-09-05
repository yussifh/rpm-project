import sys
sys.path.insert(0, ".")
import os
os.environ.setdefault("ENVIRONMENT", "development")

import uuid
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.patient import PatientProfile
from app.models.vitals import VitalReading
from app.models.prediction import RiskPrediction
from app.models.alert import Alert
from app.models.notification import Notification
from app.models.enums import DiseaseType, VitalSource
from app.services.prediction_service import PredictionService

PATIENT_ID_STR = "af72b229-31eb-4189-9f76-d49d42d3601c"

def main():
    db = SessionLocal()
    patient = db.query(PatientProfile).filter_by(id=uuid.UUID(PATIENT_ID_STR)).first()
    if not patient:
        print("Patient not found")
        sys.exit(1)

    # Clear existing vitals/predictions/alerts/notifications for a clean, realistic seed
    db.query(Notification).filter(
        Notification.user_id == patient.user_id
    ).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.patient_id == patient.id).delete(synchronize_session=False)
    db.query(RiskPrediction).filter(RiskPrediction.patient_id == patient.id).delete(synchronize_session=False)
    db.query(VitalReading).filter(VitalReading.patient_id == patient.id).delete(synchronize_session=False)
    db.commit()

    # Ensure height/weight present for BMI
    if not patient.height_cm or not patient.weight_kg:
        patient.height_cm = 170
        patient.weight_kg = 74
        db.commit()

    now = datetime.now(timezone.utc)

    # Build ~14 days of readings, roughly twice a day, with realistic values
    # and a deliberate drift on some fields so trends are meaningful:
    #   - blood glucose trends upward over the window (150 -> ~205)
    #   - systolic BP holds elevated (~150) with some variance
    #   - heart rate stable-ish mid/high-70s to low-80s
    readings = []
    days = 14
    readings_per_day = 2
    for day in range(days, 0, -1):
        for slot in range(readings_per_day):
            t = now - timedelta(days=day) + timedelta(hours=slot * 10 + 4)
            # Progress factor 0..1 moving toward "today"
            progress = (days - day) / max(days - 1, 1)
            glucose = round(150 + progress * 55 + (uuid.uuid4().int % 14) - 7, 1)
            systolic = round(138 + (uuid.uuid4().int % 30) - 5 + progress * 4, 0)
            diastolic = round(systolic * 0.66, 0)
            hr = round(74 + (uuid.uuid4().int % 12) - 3, 0)
            spo2 = round(95 + (uuid.uuid4().int % 4), 1)
            temp = round(36.5 + (uuid.uuid4().int % 5) / 10.0, 1)
            rr = round(15 + (uuid.uuid4().int % 4), 0)

            readings.append(
                VitalReading(
                    patient_id=patient.id,
                    recorded_at=t,
                    source=VitalSource.MANUAL,
                    blood_pressure_systolic=int(systolic),
                    blood_pressure_diastolic=int(diastolic),
                    heart_rate_bpm=int(hr),
                    blood_glucose_mg_dl=glucose,
                    spo2_percent=float(spo2),
                    temperature_celsius=float(temp),
                    respiratory_rate=int(rr),
                    weight_kg=patient.weight_kg,
                )
            )

    db.add_all(readings)
    db.commit()
    print(f"Seeded {len(readings)} vitals readings.")

    # Run a prediction for each disease through the REAL pipeline so
    # predictions, reasons, and recommendations are all authentic.
    svc = PredictionService(db)
    for disease in [DiseaseType.DIABETES, DiseaseType.HYPERTENSION, DiseaseType.STROKE]:
        try:
            pred = svc.predict(patient.id, disease)
            print(f"  {disease.value}: {pred.risk_level.value} (score {pred.risk_score:.3f}), {len(pred.recommendations)} recs")
        except Exception as e:
            print(f"  {disease.value}: ERROR {e}")

    db.close()
    print("Done.")

if __name__ == "__main__":
    main()
