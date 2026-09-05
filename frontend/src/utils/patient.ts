/** Computes age in whole years from an ISO date-of-birth string. */
export function ageFromDateOfBirth(dateOfBirth: string): number {
  const dob = new Date(dateOfBirth);
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age -= 1;
  }
  return age;
}

/** Short, human-friendly patient reference derived from the UUID —
 * not a real MRN (this app has no billing/MRN system), just a stable
 * short label so a chart doesn't have to show the full UUID. */
export function shortPatientRef(patientId: string): string {
  return patientId.slice(0, 8).toUpperCase();
}
