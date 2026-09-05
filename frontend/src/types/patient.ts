export type Gender = "male" | "female" | "other";

export interface PatientProfile {
  id: string;
  user_id: string;
  date_of_birth: string;
  gender: Gender;
  blood_group: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  chronic_conditions_summary: string | null;
  primary_condition: "stroke" | "diabetes" | "hypertension" | null;
  created_at: string;
  // Present on admin list & get-by-id responses; absent on /me.
  full_name?: string;
  email?: string;
  phone_number?: string | null;
}
