import { Link, useParams } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AlertsList } from "@/components/ui/AlertsList";
import { VitalReadout } from "@/components/ui/VitalReadout";
import { RiskHeadline } from "@/components/ui/RiskHeadline";
import { VitalsTrendChart } from "@/components/charts/VitalsTrendChart";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import { vitalsApi } from "@/services/vitalsApi";
import { predictionApi } from "@/services/predictionApi";
import { alertApi } from "@/services/alertApi";
import { statusForRange, statusForSpo2 } from "@/utils/vitalsStatus";
import { DISEASE_PLAIN_NAME } from "@/utils/plainLanguage";
import type { RiskLevel, RiskPrediction } from "@/types/prediction";

const RISK_TONE: Record<RiskLevel, "stable" | "warning" | "critical" | "info"> = {
  low: "stable",
  moderate: "info",
  high: "warning",
  critical: "critical",
};

const RISK_RANK: Record<RiskLevel, number> = { low: 0, moderate: 1, high: 2, critical: 3 };

/** Admin view of a single patient's health records — vitals history,
 *  latest AI risk assessment (plain-language), and alerts. Reuses the
 *  same read endpoints the patient sees; the backend already grants
 *  admins read access to every patient (patient-access rule). */
export function PatientRecordsPage() {
  const { patientId } = useParams<{ patientId: string }>();

  const { data: patient, error: patientError } = useAsyncData(
    () => (patientId ? patientApi.getById(patientId) : Promise.resolve(null)),
    [patientId]
  );
  const { data: readings, isLoading: readingsLoading } = useAsyncData(
    () => (patientId ? vitalsApi.list(patientId) : Promise.resolve([])),
    [patientId]
  );
  const { data: predictions, isLoading: predictionsLoading } = useAsyncData(
    () => (patientId ? predictionApi.list(patientId) : Promise.resolve([])),
    [patientId]
  );
  const { data: allAlerts } = useAsyncData(() => alertApi.listAll(), []);

  if (patientError) {
    return (
      <div>
        <p className="rounded-lg bg-status-critical/10 px-3 py-2 text-sm text-status-critical">
          Couldn't load this patient's records. Try refreshing the page.
        </p>
        <Link to="/admin/patients" className="mt-4 inline-block text-sm font-medium text-teal-600 hover:underline">
          Back to patients
        </Link>
      </div>
    );
  }

  if (!patient) {
    return <p className="text-sm text-ink-soft">Loading patient…</p>;
  }

  const latest = readings?.[0];

  const latestByDisease = new Map<string, RiskPrediction>();
  for (const p of predictions ?? []) {
    if (!latestByDisease.has(p.disease_type)) latestByDisease.set(p.disease_type, p);
  }
  const highestRisk = [...latestByDisease.values()].sort(
    (a, b) => RISK_RANK[b.risk_level] - RISK_RANK[a.risk_level]
  )[0];

  const patientAlerts = (allAlerts ?? []).filter(
    (a) => a.patient_id === patient.id && a.status !== "resolved"
  );

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/admin/patients" className="text-sm font-medium text-teal-600 hover:underline">
            ← Back to patients
          </Link>
          <h1 className="mt-1 font-display text-2xl font-bold text-ink">{patient.full_name ?? "Patient"}</h1>
          <p className="mt-1 text-sm text-ink-soft">{patient.email}</p>
        </div>
        {patient.primary_condition && (
          <Badge tone="info">{DISEASE_PLAIN_NAME[patient.primary_condition]}</Badge>
        )}
      </div>

      {highestRisk && (
        <Card className="mt-6 border-status-warning">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">
            Current Health Status
          </p>
          <div className="mt-2 flex items-center gap-2">
            <Badge tone={RISK_TONE[highestRisk.risk_level]}>{highestRisk.risk_level} concern</Badge>
            <span className="text-sm capitalize text-ink-soft">
              {DISEASE_PLAIN_NAME[highestRisk.disease_type]}
            </span>
          </div>
          <p className="mt-2 text-sm text-ink">
            <RiskHeadline prediction={highestRisk} />
          </p>
        </Card>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Card>
          <VitalReadout
            label="Blood Pressure"
            value={
              latest?.blood_pressure_systolic && latest?.blood_pressure_diastolic
                ? `${latest.blood_pressure_systolic}/${latest.blood_pressure_diastolic}`
                : "—/—"
            }
            unit="mmHg"
            status={statusForRange(latest?.blood_pressure_systolic, 140, 180)}
          />
        </Card>
        <Card>
          <VitalReadout
            label="Heart Rate"
            value={latest?.heart_rate_bpm ?? "—"}
            unit="bpm"
            status={statusForRange(latest?.heart_rate_bpm, 120, 180)}
          />
        </Card>
        <Card>
          <VitalReadout
            label="Glucose"
            value={latest?.blood_glucose_mg_dl ?? "—"}
            unit="mg/dL"
            status={statusForRange(latest?.blood_glucose_mg_dl, 200, 300)}
          />
        </Card>
        <Card>
          <VitalReadout
            label="SpO2"
            value={latest?.spo2_percent ?? "—"}
            unit="%"
            status={statusForSpo2(latest?.spo2_percent)}
          />
        </Card>
        <Card>
          <VitalReadout label="Weight" value={latest?.weight_kg ?? "—"} unit="kg" />
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Latest AI Assessment</h2>
        <div className="mt-4">
          {predictionsLoading ? (
            <p className="text-sm text-ink-soft">Loading…</p>
          ) : predictions && predictions.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {[...latestByDisease.values()].map((prediction) => (
                <div key={prediction.id} className="rounded-lg border border-surface-border p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-display text-sm font-bold capitalize text-ink">
                      {DISEASE_PLAIN_NAME[prediction.disease_type]}
                    </h3>
                    <Badge tone={RISK_TONE[prediction.risk_level]}>
                      {prediction.risk_level} concern
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm text-ink">
                    <RiskHeadline prediction={prediction} />
                  </p>
                  {prediction.reasons.length > 0 && (
                    <ul className="mt-2 list-inside list-disc space-y-1">
                      {prediction.reasons.slice(0, 3).map((reason) => (
                        <li key={reason} className="text-sm text-ink-soft">
                          {reason}
                        </li>
                      ))}
                    </ul>
                  )}
                  {prediction.recommendations.length > 0 && (
                    <div className="mt-3 rounded-lg bg-teal-50 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-teal-700">
                        Recommendation
                      </p>
                      <ul className="mt-1 list-inside list-disc space-y-1">
                        {prediction.recommendations.slice(0, 2).map((rec) => (
                          <li key={rec} className="text-sm text-ink">
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-ink-soft">No AI assessments yet.</p>
          )}
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Vitals Trend</h2>
        <div className="mt-4">
          {readingsLoading ? (
            <p className="text-sm text-ink-soft">Loading…</p>
          ) : (
            <VitalsTrendChart readings={readings ?? []} />
          )}
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Alerts</h2>
        <div className="mt-4">
          <AlertsList alerts={patientAlerts} emptyMessage="No active alerts for this patient." />
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Vitals History</h2>
        {!readings || readings.length === 0 ? (
          <p className="mt-4 text-sm text-ink-soft">No readings logged yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs uppercase tracking-wide text-ink-soft">
                  <th className="py-2 pr-4 font-medium">When</th>
                  <th className="py-2 pr-4 font-medium">BP</th>
                  <th className="py-2 pr-4 font-medium">HR</th>
                  <th className="py-2 pr-4 font-medium">Glucose</th>
                  <th className="py-2 pr-4 font-medium">SpO2</th>
                  <th className="py-2 pr-4 font-medium">Weight</th>
                </tr>
              </thead>
              <tbody>
                {readings.map((r) => (
                  <tr key={r.id} className="border-b border-surface-border last:border-0">
                    <td className="py-2 pr-4 readout text-ink-soft">{new Date(r.recorded_at).toLocaleString()}</td>
                    <td className="py-2 pr-4 readout text-ink">
                      {r.blood_pressure_systolic && r.blood_pressure_diastolic
                        ? `${r.blood_pressure_systolic}/${r.blood_pressure_diastolic}`
                        : "—"}
                    </td>
                    <td className="py-2 pr-4 readout text-ink">{r.heart_rate_bpm ?? "—"}</td>
                    <td className="py-2 pr-4 readout text-ink">{r.blood_glucose_mg_dl ?? "—"}</td>
                    <td className="py-2 pr-4 readout text-ink">{r.spo2_percent ?? "—"}</td>
                    <td className="py-2 pr-4 readout text-ink">
                      {r.weight_kg ? `${r.weight_kg} kg` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
