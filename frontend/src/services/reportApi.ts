import { apiClient } from "./apiClient";

export const reportApi = {
  /** Downloads the AI-generated patient summary PDF (vitals, active
   * medications, alerts, latest risk predictions) and triggers a save. */
  async downloadSummary(patientId: string, patientName?: string): Promise<void> {
    const { data } = await apiClient.get(`/patients/${patientId}/reports/summary`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    const safeName = (patientName ?? "patient").replace(/\s+/g, "_").toLowerCase();
    link.download = `${safeName}_health_report.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /** Downloads the patient's complete vitals history as a CSV file they can
   * keep for the future (open in Excel, share with a clinician). */
  async downloadVitalsHistory(patientId: string, patientName?: string): Promise<void> {
    const { data } = await apiClient.get(`/patients/${patientId}/reports/vitals-history`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([data], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    const safeName = (patientName ?? "patient").replace(/\s+/g, "_").toLowerCase();
    link.download = `${safeName}_vitals_history.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};
