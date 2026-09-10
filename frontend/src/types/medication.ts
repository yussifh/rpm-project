export type MedicationLogStatus = "taken" | "missed" | "skipped";

export interface Medication {
  id: string;
  patient_id: string;
  name: string;
  dosage: string;
  frequency: string;
  instructions: string | null;
  start_date: string; // YYYY-MM-DD
  end_date: string | null;
  is_active: boolean;
  created_at: string;
}

export interface MedicationCreatePayload {
  name: string;
  dosage: string;
  frequency: string;
  instructions?: string;
  start_date: string;
  end_date?: string;
}

export interface MedicationLog {
  id: string;
  medication_id: string;
  scheduled_at: string;
  status: MedicationLogStatus;
  taken_at: string | null;
  created_at: string;
}

export interface MedicationLogCreatePayload {
  scheduled_at: string;
  status: MedicationLogStatus;
  taken_at?: string;
}
