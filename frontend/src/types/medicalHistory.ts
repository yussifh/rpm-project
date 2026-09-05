export interface MedicalHistoryEntry {
  id: string;
  patient_id: string;
  condition_name: string;
  diagnosed_date: string | null;
  notes: string | null;
  recorded_by: string | null;
  created_at: string;
}

export interface MedicalHistoryCreatePayload {
  condition_name: string;
  diagnosed_date?: string;
  notes?: string;
}
