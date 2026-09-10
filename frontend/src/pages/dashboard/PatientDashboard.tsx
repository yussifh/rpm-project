import { VitalReadout } from "@/components/ui/VitalReadout";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AlertsList } from "@/components/ui/AlertsList";
import { DashboardWelcomeBanner } from "@/components/ui/DashboardWelcomeBanner";
import { VitalsTrendChart } from "@/components/charts/VitalsTrendChart";
import { useAuth } from "@/context/useAuth";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import { vitalsApi } from "@/services/vitalsApi";
import { predictionApi } from "@/services/predictionApi";
import { alertApi } from "@/services/alertApi";
import { statusForRange, statusForSpo2 } from "@/utils/vitalsStatus";
import { DISEASE_PLAIN_NAME } from "@/utils/plainLanguage";
import { RiskHeadline } from "@/components/ui/RiskHeadline";
import type { RiskLevel, RiskPrediction } from "@/types/prediction";

const RISK_TONE: Record<RiskLevel, "stable" | "warning" | "critical" | "info"> = {
  low: "stable",
  moderate: "info",
  high: "warning",
  critical: "critical",
};

const RISK_RANK: Record<RiskLevel, number> = { low: 0, moderate: 1, high: 2, critical: 3 };

export function PatientDashboard() {
  const { user } = useAuth();
  const { data: profile, error: profileError } = useAsyncData(() => patientApi.getMe(), []);
  const { data: readings, isLoading } = useAsyncData(
    () => (profile ? vitalsApi.list(profile.id) : Promise.resolve([])),
    [profile?.id]
  );
  const { data: predictions } = useAsyncData(
    () => (profile ? predictionApi.list(profile.id) : Promise.resolve([])),
    [profile?.id]
  );
  const { data: alerts } = useAsyncData(() => alertApi.listMine(), []);

  const latest = readings?.[0];

  // Highest-risk current prediction across the three diseases, to
  // headline "Current risk status" the way the spec's Health Overview
  // section describes — a patient with one high-risk condition should
  // see that surfaced, not buried behind a lower-risk one.
  const latestByDisease = new Map<string, RiskPrediction>();
  for (const p of predictions ?? []) {
    if (!latestByDisease.has(p.disease_type)) latestByDisease.set(p.disease_type, p);
  }
  const highestRisk = [...latestByDisease.values()].sort(
    (a, b) => RISK_RANK[b.risk_level] - RISK_RANK[a.risk_level]
  )[0];

  const activeAlerts = (alerts ?? []).filter((a) => a.status !== "resolved");

  return (
    <div>
      <DashboardWelcomeBanner variant="patient" name={user?.full_name} subtitle="Your latest readings" />

      {profileError && (
        <p className="mt-4 rounded-lg bg-status-critical/10 px-3 py-2 text-sm text-status-critical">
          Couldn't load your profile. Try refreshing the page.
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Current Health Status</p>
          {highestRisk ? (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <Badge tone={RISK_TONE[highestRisk.risk_level]}>{highestRisk.risk_level} concern</Badge>
                <span className="text-sm capitalize text-ink-soft">
                  {DISEASE_PLAIN_NAME[highestRisk.disease_type]}
                </span>
              </div>
              <p className="mt-2 text-sm text-ink">
                <RiskHeadline prediction={highestRisk} />
              </p>
            </div>
          ) : (
            <p className="mt-2 text-sm text-ink-soft">No AI assessment yet.</p>
          )}
        </Card>
        <Card>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Active Alerts</p>
          <p className="readout mt-1 text-3xl font-medium text-teal-600">{activeAlerts.length}</p>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
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
        <h2 className="font-display text-sm font-bold text-ink">Vitals Trend</h2>
        <div className="mt-4">
          {isLoading ? <p className="text-sm text-ink-soft">Loading…</p> : <VitalsTrendChart readings={readings ?? []} />}
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Alerts</h2>
        <div className="mt-4">
          <AlertsList alerts={activeAlerts} emptyMessage="No active alerts." />
        </div>
      </Card>
    </div>
  );
}
