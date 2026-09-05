import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import { medicationApi } from "@/services/medicationApi";
import type { MedicationLogStatus } from "@/types/medication";

const DOSE_OPTIONS: { label: string; value: MedicationLogStatus }[] = [
  { label: "Taken", value: "taken" },
  { label: "Missed", value: "missed" },
  { label: "Skipped", value: "skipped" },
];

export function MedicationsPage() {
  const { data: profile, error: profileError } = useAsyncData(() => patientApi.getMe(), []);
  const { data: medications, isLoading, error, refetch } = useAsyncData(
    () => (profile ? medicationApi.listForPatient(profile.id) : Promise.resolve([])),
    [profile?.id]
  );
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [loggedMessage, setLoggedMessage] = useState<string | null>(null);

  async function logDose(medicationId: string, status: MedicationLogStatus) {
    setPendingId(medicationId);
    setLoggedMessage(null);
    try {
      await medicationApi.logDose(medicationId, {
        scheduled_at: new Date().toISOString(),
        status,
        taken_at: status === "taken" ? new Date().toISOString() : undefined,
      });
      setLoggedMessage(`Dose marked as ${status}.`);
      refetch();
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-ink">Medications</h1>
      <p className="mt-1 text-sm text-ink-soft">Your current prescriptions and adherence log.</p>

      {error && <p className="mt-4 text-sm text-status-critical">Couldn't load medications.</p>}
      {profileError && (
        <p className="mt-4 rounded-lg bg-status-critical/10 px-3 py-2 text-sm text-status-critical">
          Couldn't load your profile. Try refreshing the page.
        </p>
      )}
      {loggedMessage && <p className="mt-4 text-sm text-status-stable">{loggedMessage}</p>}

      <div className="mt-6 space-y-3">
        {isLoading ? (
          <p className="text-sm text-ink-soft">Loading…</p>
        ) : !medications || medications.length === 0 ? (
          <Card>
            <p className="text-sm text-ink-soft">No medications have been prescribed yet.</p>
          </Card>
        ) : (
          medications.map((med) => (
            <Card key={med.id}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-ink">{med.name}</p>
                    <Badge tone={med.is_active ? "stable" : "neutral"}>{med.is_active ? "Active" : "Ended"}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-ink-soft">
                    {med.dosage} · {med.frequency}
                  </p>
                  {med.instructions && <p className="mt-1 text-xs text-ink-soft">{med.instructions}</p>}
                  <p className="mt-1 text-xs text-ink-soft">
                    Started {med.start_date}
                    {med.end_date ? ` · Ends ${med.end_date}` : ""}
                  </p>
                </div>
                {med.is_active && (
                  <div className="flex shrink-0 gap-2">
                    {DOSE_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => logDose(med.id, opt.value)}
                        disabled={pendingId === med.id}
                        className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-sunken disabled:opacity-60"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
