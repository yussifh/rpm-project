export interface PatientCreatePayload {
  email: string;
  password: string;
  full_name: string;
  phone_number?: string;
  date_of_birth: string;
  gender: "male" | "female" | "other";
  blood_group?: string;
}
