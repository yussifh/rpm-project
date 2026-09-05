import { useState, type FormEvent } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { VitalsTrendChart } from "@/components/charts/VitalsTrendChart";
import { VitalTrendCard } from "@/components/charts/VitalTrendCard";
import { useAsyncData } from "@/hooks/useAsyncData";
import { useAuth } from "@/context/useAuth";
import { patientApi } from "@/services/patientApi";
import { vitalsApi } from "@/services/vitalsApi";
import { reportApi } from "@/services/reportApi";
import { assessmentApi } from "@/services/assessmentApi";
import { CONDITION_ML_VITAL_FIELDS, SYMPTOM_CHECKLISTS } from "@/types/diseaseAssessment";
import type { VitalReadingCreatePayload, VitalSubmissionResult } from "@/types/vitals";
import type { DiseaseType, RiskLevel } from "@/types/prediction";

const inputClass = "mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500";
const labelClass = "block text-xs font-medium uppercase tracking-wide text-ink-soft";

const initialForm: VitalReadingCreatePayload = {};

const CONDITION_OPTIONS: { value: DiseaseType; label: string; blurb: string }[] = [
  { value: "diabetes", label: "Diabetes", blurb: "Blood glucose, blood pressure" },
  { value: "hypertension", label: "Hypertension", blurb: "Blood pressure, heart rate, glucose" },
  { value: "stroke", label: "Stroke", blurb: "Blood pressure, heart rate, glucose" },
];

const FIELD_META: Record<
  string,
  { label: string; unit: string; type: "int" | "float"; min: number; max: number; step?: string }
> = {
  blood_pressure_systolic: { label: "Systolic (mmHg)", unit: "mmHg", type: "int", min: 50, max: 300 },
  blood_pressure_diastolic: { label: "Diastolic (mmHg)", unit: "mmHg", type: "int", min: 30, max: 200 },
  heart_rate_bpm: { label: "Heart rate (bpm)", unit: "bpm", type: "int", min: 20, max: 250 },
  blood_glucose_mg_dl: { label: "Glucose (mg/dL)", unit: "mg/dL", type: "float", min: 20, max: 800 },
};

const OTHER_FIELD_META: typeof FIELD_META = {
  spo2_percent: { label: "SpO2 (%)", unit: "%", type: "float", min: 50, max: 100 },
  temperature_celsius: { label: "Temperature (°C)", unit: "°C", type: "float", min: 25, max: 45, step: "0.1" },
  respiratory_rate: { label: "Respiratory rate (breaths/min)", unit: "breaths/min", type: "int", min: 5, max: 60 },
  weight_kg: { label: "Weight (kg)", unit: "kg", type: "float", min: 2, max: 400, step: "0.1" },
};

const RISK_TONE: Record<RiskLevel, "stable" | "warning" | "critical" | "info"> = {
  low: "stable",
  moderate: "info",
  high: "warning",
  critical: "critical",
};

function relevantFieldKeys(conditions: DiseaseType[]): string[] {
  const keys = new Set<string>();
  for (const c of conditions) {
    for (const k of CONDITION_ML_VITAL_FIELDS[c]) keys.add(k);
  }
  return [...keys];
}

export function VitalsPage() {
  const { user } = useAuth();
  const { data: profile, error: profileError } = useAsyncData(() => patientApi.getMe(), []);
  const { data: readings, isLoading, error, refetch } = useAsyncData(
    () => (profile ? vitalsApi.list(profile.id) : Promise.resolve([])),
    [profile?.id]
  );
  const {
    data: trendsResponse,
    isLoading: trendsLoading,
    refetch: refetchTrends,
  } = useAsyncData(() => (profile ? vitalsApi.trends(profile.id, 90) : Promise.resolve(null)), [profile?.id]);

  // --- Condition-based vitals entry workflow state ---
  // step 1: pick condition(s) — `pickerOpen` true until the patient continues.
  // step 2: enter only the vitals those conditions need (+ optional extras).
  // step 3 (modal): review/confirm before anything is analyzed.
  // step 4: results, one card per selected condition.
  const [pickerOpen, setPickerOpen] = useState(true);
  const [selectedConditions, setSelectedConditions] = useState<DiseaseType[]>([]);
  const [form, setForm] = useState<VitalReadingCreatePayload>(initialForm);
  const [showOtherFields, setShowOtherFields] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [result, setResult] = useState<VitalSubmissionResult | null>(null);

  const [symptomsByCondition, setSymptomsByCondition] = useState<Partial<Record<DiseaseType, Record<string, boolean>>>>({});
  const [assessmentSubmitting, setAssessmentSubmitting] = useState(false);
  const [assessmentSaved, setAssessmentSaved] = useState(false);

  function toggleSymptom(condition: DiseaseType, key: string, checked: boolean) {
    setSymptomsByCondition((prev) => ({
      ...prev,
      [condition]: { ...prev[condition], [key]: checked },
    }));
  }

  async function handleAssessmentSubmit(e: FormEvent) {
    e.preventDefault();
    if (selectedConditions.length === 0 || !profile) return;
    setAssessmentSubmitting(true);
    setAssessmentSaved(false);
    try {
      // One assessment per selected condition — mirrors how vitals
      // submission itself never blends conditions together, so a
      // symptom check for Diabetes + Hypertension saves as two distinct
      // records, each against its own condition's checklist answers.
      await Promise.all(
        selectedConditions.map((condition) =>
          assessmentApi.submit(profile.id, {
            disease_type: condition,
            symptoms: symptomsByCondition[condition] ?? {},
          })
        )
      );
      setSymptomsByCondition({});
      setAssessmentSaved(true);
    } finally {
      setAssessmentSubmitting(false);
    }
  }

  function update<K extends keyof VitalReadingCreatePayload>(key: K, value: VitalReadingCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleCondition(condition: DiseaseType) {
    setSelectedConditions((prev) =>
      prev.includes(condition) ? prev.filter((c) => c !== condition) : [...prev, condition]
    );
  }

  function handleContinueFromPicker() {
    if (selectedConditions.length === 0) return;
    const stillRequired = new Set(relevantFieldKeys(selectedConditions));
    setForm((prev) => {
      const next = { ...prev };
      for (const key of Object.keys(FIELD_META)) {
        if (!stillRequired.has(key)) delete (next as Record<string, unknown>)[key];
      }
      return next;
    });
    setPickerOpen(false);
  }

  function handleAnalyzeClick(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setShowConfirm(true);
  }

  async function handleConfirm() {
    if (!profile) return;
    setIsSubmitting(true);
    try {
      const submission = await vitalsApi.record(profile.id, { ...form, conditions: selectedConditions });
      setResult(submission);
      setShowConfirm(false);
      refetch();
      refetchTrends();
    } catch (err) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Couldn't save reading. At least one measurement is required.";
      setFormError(message);
      setShowConfirm(false);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleLogAnother() {
    setResult(null);
    setForm(initialForm);
    setSelectedConditions([]);
    setShowOtherFields(false);
    setSymptomsByCondition({});
    setAssessmentSaved(false);
    setPickerOpen(true);
  }

  const requiredKeys = new Set(relevantFieldKeys(selectedConditions));

  const enteredEntries = [
    ...Object.entries(FIELD_META).filter(([key]) => requiredKeys.has(key)),
    ...Object.entries(OTHER_FIELD_META),
  ].filter(([key]) => (form as Record<string, unknown>)[key] !== undefined && (form as Record<string, unknown>)[key] !== "");

  const filteredTrends =
    selectedConditions.length > 0
      ? (trendsResponse?.trends ?? []).filter((t) =>
          selectedConditions.some((c) => CONDITION_ML_VITAL_FIELDS[c].includes(t.field))
        )
      : trendsResponse?.trends ?? [];

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink">My Vitals</h1>
          <p className="mt-1 text-sm text-ink-soft">Log a new reading and review your history.</p>
        </div>
        <button
          onClick={() => profile && reportApi.downloadSummary(profile.id, user?.full_name)}
          disabled={!profile}
          className="rounded-lg border border-surface-border px-3 py-2 text-xs font-medium text-ink hover:bg-surface-sunken disabled:opacity-60"
        >
          Download AI health report
        </button>
      </div>

      {profileError && (
        <p className="mt-4 rounded-lg bg-status-critical/10 px-3 py-2 text-sm text-status-critical">
          Couldn't load your profile, so vitals can't be analyzed right now. Try refreshing the page — if
          this keeps happening, please contact support.
        </p>
      )}

      <Card className="mt-6">
        {result ? (
          <div>
            <div className="flex items-center justify-between">
              <h2 className="font-display text-sm font-bold text-ink">AI Health Assessment Results</h2>
              <button
                type="button"
                onClick={handleLogAnother}
                className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-sunken"
              >
                Log another reading
              </button>
            </div>
            <p className="mt-1 text-xs text-ink-soft">
              Reading saved {new Date(result.vital.recorded_at).toLocaleString()}. Each selected condition below was
              assessed separately by its own trained model — not a diagnosis.
            </p>

            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {result.predictions.map((prediction) => {
                const relevantFields = new Set(CONDITION_ML_VITAL_FIELDS[prediction.disease_type]);
                const conditionTrends = (trendsResponse?.trends ?? []).filter((t) => relevantFields.has(t.field));
                return (
                  <div key={prediction.id} className="rounded-lg border border-surface-border p-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-display text-sm font-bold capitalize text-ink">{prediction.disease_type}</h3>
                      <Badge tone={RISK_TONE[prediction.risk_level]}>{prediction.risk_level} risk</Badge>
                    </div>
                    <p className="mt-2 text-sm text-ink">
                      Risk score <span className="readout font-medium">{(prediction.risk_score * 100).toFixed(0)}%</span>
                    </p>
                    {prediction.reasons.length > 0 && (
                      <ul className="mt-2 list-inside list-disc space-y-1">
                        {prediction.reasons.map((reason) => (
                          <li key={reason} className="text-sm text-ink-soft">
                            {reason}
                          </li>
                        ))}
                      </ul>
                    )}
                    {conditionTrends.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium uppercase tracking-wide text-ink-soft">Relevant Trend</p>
                        <ul className="mt-1 space-y-1">
                          {conditionTrends.map((t) => (
                            <li key={t.field} className="text-sm text-ink-soft">
                              {t.summary}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {prediction.recommendations.length > 0 && (
                      <div className="mt-3 rounded-lg bg-teal-50 p-3">
                        <p className="text-xs font-medium uppercase tracking-wide text-teal-700">AI Recommendation</p>
                        <ul className="mt-1 list-inside list-disc space-y-1">
                          {prediction.recommendations.map((rec) => (
                            <li key={rec} className="text-sm text-ink">
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}

              {result.skipped.map((skip) => (
                <div key={skip.disease_type} className="rounded-lg border border-dashed border-surface-border p-4">
                  <h3 className="font-display text-sm font-bold capitalize text-ink-soft">{skip.disease_type}</h3>
                  <p className="mt-2 text-sm text-ink-soft">Couldn't generate an assessment: {skip.reason}</p>
                </div>
              ))}
            </div>
          </div>
        ) : pickerOpen ? (
          <div>
            <h2 className="font-display text-sm font-bold text-ink">Select condition(s) to monitor</h2>
            <p className="mt-1 text-xs text-ink-soft">
              Choose at least one. This decides which vitals you'll enter and which AI model(s) assess this reading.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {CONDITION_OPTIONS.map((opt) => {
                const checked = selectedConditions.includes(opt.value);
                return (
                  <label
                    key={opt.value}
                    className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                      checked ? "border-teal-500 bg-teal-50" : "border-surface-border hover:border-teal-300"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <input type="checkbox" checked={checked} onChange={() => toggleCondition(opt.value)} />
                      <span className="font-display text-sm font-bold text-ink">{opt.label}</span>
                    </div>
                    <p className="mt-1 text-xs text-ink-soft">{opt.blurb}</p>
                  </label>
                );
              })}
            </div>
            <button
              type="button"
              onClick={handleContinueFromPicker}
              disabled={selectedConditions.length === 0}
              className="mt-4 rounded-lg bg-teal-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-600 disabled:opacity-60"
            >
              Continue
            </button>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between">
              <h2 className="font-display text-sm font-bold text-ink">
                Enter vitals for{" "}
                <span className="capitalize text-teal-600">{selectedConditions.join(", ")}</span>
              </h2>
              <button
                type="button"
                onClick={() => setPickerOpen(true)}
                className="text-xs font-medium text-teal-600 hover:underline"
              >
                Change condition(s)
              </button>
            </div>

            <form onSubmit={handleAnalyzeClick} className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {Object.entries(FIELD_META)
                .filter(([key]) => requiredKeys.has(key))
                .map(([key, meta]) => (
                  <div key={key}>
                    <label className={labelClass}>{meta.label}</label>
                    <input
                      type="number"
                      step={meta.step}
                      min={meta.min}
                      max={meta.max}
                      value={((form as Record<string, unknown>)[key] as number | undefined) ?? ""}
                      onChange={(e) => update(key as keyof VitalReadingCreatePayload, (e.target.value ? Number(e.target.value) : undefined) as never)}
                      className={inputClass}
                    />
                  </div>
                ))}

              <div className="col-span-2 sm:col-span-4">
                <button
                  type="button"
                  onClick={() => setShowOtherFields((v) => !v)}
                  className="text-xs font-medium text-ink-soft hover:text-ink"
                >
                  {showOtherFields ? "Hide" : "Add"} other measurements (weight, SpO2, temperature…)
                </button>
              </div>

              {showOtherFields &&
                Object.entries(OTHER_FIELD_META).map(([key, meta]) => (
                  <div key={key}>
                    <label className={labelClass}>{meta.label}</label>
                    <input
                      type="number"
                      step={meta.step}
                      min={meta.min}
                      max={meta.max}
                      value={((form as Record<string, unknown>)[key] as number | undefined) ?? ""}
                      onChange={(e) => update(key as keyof VitalReadingCreatePayload, (e.target.value ? Number(e.target.value) : undefined) as never)}
                      className={inputClass}
                    />
                  </div>
                ))}

              <div className="col-span-2 sm:col-span-4">
                <label className={labelClass}>Notes</label>
                <input
                  placeholder="Anything you'd like noted about this reading"
                  value={form.notes ?? ""}
                  onChange={(e) => update("notes", e.target.value)}
                  className={inputClass}
                />
              </div>

              {formError && <p className="col-span-2 sm:col-span-4 text-sm text-status-critical">{formError}</p>}

              <div className="col-span-2 sm:col-span-4">
                <button
                  type="submit"
                  disabled={!profile}
                  className="rounded-lg bg-teal-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-600 disabled:opacity-60"
                >
                  Analyze
                </button>
              </div>
            </form>
          </div>
        )}
      </Card>

      {showConfirm && (
        <Modal title="Review your vital signs" onClose={() => setShowConfirm(false)}>
          <p className="text-sm text-ink-soft">
            Please review your vital signs carefully. These values will be used by the AI/ML system to generate
            your health assessment. If any information is incorrect, select Edit Vitals before continuing.
          </p>

          <div className="mt-4">
            <p className={labelClass}>Condition(s) selected</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {selectedConditions.map((c) => (
                <Badge key={c} tone="info">
                  {c}
                </Badge>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <p className={labelClass}>Values entered</p>
            {enteredEntries.length === 0 ? (
              <p className="mt-1 text-sm text-ink-soft">No values entered.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {enteredEntries.map(([key, meta]) => (
                  <li key={key} className="flex justify-between text-sm">
                    <span className="text-ink-soft">{meta.label.replace(/\s*\(.*\)/, "")}</span>
                    <span className="readout font-medium text-ink">
                      {(form as Record<string, unknown>)[key] as number} {meta.unit}
                    </span>
                  </li>
                ))}
                {form.notes && (
                  <li className="flex justify-between text-sm">
                    <span className="text-ink-soft">Notes</span>
                    <span className="text-ink">{form.notes}</span>
                  </li>
                )}
              </ul>
            )}
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowConfirm(false)}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-ink hover:bg-surface-sunken"
            >
              Edit Vitals
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isSubmitting}
              className="rounded-lg bg-teal-500 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
            >
              {isSubmitting ? "Analyzing…" : "Confirm"}
            </button>
          </div>
        </Modal>
      )}

      {selectedConditions.length > 0 && (
        <Card className="mt-6">
          <h2 className="font-display text-sm font-bold text-ink">Today's symptom check</h2>
          <p className="mt-1 text-xs text-ink-soft">
            Track how you're feeling today for {selectedConditions.join(", ")} — this feeds your AI health
            assessment for those condition(s).
          </p>
          <form onSubmit={handleAssessmentSubmit} className="mt-4 space-y-5">
            {selectedConditions.map((condition) => (
              <div key={condition}>
                <p className="text-xs font-semibold capitalize text-ink">{condition}</p>
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {SYMPTOM_CHECKLISTS[condition].map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-2 text-sm text-ink">
                      <input
                        type="checkbox"
                        checked={symptomsByCondition[condition]?.[key] ?? false}
                        onChange={(e) => toggleSymptom(condition, key, e.target.checked)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            ))}
            {assessmentSaved && <p className="text-sm text-status-stable">Thanks — this has been saved to your health history.</p>}
            <button
              type="submit"
              disabled={assessmentSubmitting}
              className="rounded-lg bg-teal-500 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
            >
              {assessmentSubmitting ? "Saving…" : "Submit symptom check"}
            </button>
          </form>
        </Card>
      )}

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">Trend</h2>
        {error && <p className="mt-4 text-sm text-status-critical">Couldn't load vitals history.</p>}
        <div className="mt-4">
          {isLoading ? <p className="text-sm text-ink-soft">Loading…</p> : <VitalsTrendChart readings={readings ?? []} />}
        </div>
      </Card>

      <Card className="mt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-sm font-bold text-ink">AI Trend Analysis</h2>
            <p className="mt-1 text-xs text-ink-soft">
              How each measurement has moved over the last {trendsResponse?.period_days ?? 90} days.
            </p>
          </div>
          {selectedConditions.length > 0 && (
            <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium capitalize text-teal-700">
              Scoped to: {selectedConditions.join(", ")}
            </span>
          )}
        </div>
        <div className="mt-4 space-y-3">
          {trendsLoading ? (
            <p className="text-sm text-ink-soft">Loading…</p>
          ) : !trendsResponse || trendsResponse.trends.length === 0 ? (
            <p className="text-sm text-ink-soft">Log a few readings over time to see trend analysis here.</p>
          ) : filteredTrends.length === 0 ? (
            <p className="text-sm text-ink-soft">
              No measurements relevant to {selectedConditions.join(", ") || "your selection"} logged yet.
            </p>
          ) : (
            filteredTrends.map((trend) => <VitalTrendCard key={trend.field} trend={trend} />)
          )}
        </div>
      </Card>

      <Card className="mt-6">
        <h2 className="font-display text-sm font-bold text-ink">History</h2>
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
                  <th className="py-2 pr-4 font-medium">Source</th>
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
                    <td className="py-2 pr-4 readout text-ink">{r.weight_kg ? `${r.weight_kg} kg` : "—"}</td>
                    <td className="py-2 pr-4 capitalize text-ink-soft">{r.source}</td>
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
