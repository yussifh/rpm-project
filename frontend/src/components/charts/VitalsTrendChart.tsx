import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { useMemo, useState } from "react";
import type { VitalReading } from "@/types/vitals";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface VitalsTrendChartProps {
  readings: VitalReading[];
}

type MeasurementKey =
  | "blood_pressure_systolic"
  | "blood_pressure_diastolic"
  | "heart_rate_bpm"
  | "blood_glucose_mg_dl"
  | "bmi"
  | "spo2_percent"
  | "temperature_celsius"
  | "respiratory_rate"
  | "diabetes_pedigree_function"
  | "weight_kg";

interface MetricDef {
  key: MeasurementKey;
  label: string;
  color: string;
}

const METRICS: MetricDef[] = [
  { key: "blood_pressure_systolic", label: "Systolic BP", color: "#14555A" },
  { key: "blood_pressure_diastolic", label: "Diastolic BP", color: "#2C7A7F" },
  { key: "heart_rate_bpm", label: "Heart rate", color: "#B25E1E" },
  { key: "blood_glucose_mg_dl", label: "Glucose", color: "#E2A63B" },
  { key: "bmi", label: "BMI", color: "#5B3F8E" },
  { key: "spo2_percent", label: "SpO2", color: "#2563EB" },
  { key: "temperature_celsius", label: "Temperature", color: "#DC2626" },
  { key: "respiratory_rate", label: "Respiratory rate", color: "#0F766E" },
  { key: "diabetes_pedigree_function", label: "Diabetes pedigree", color: "#A855F7" },
  { key: "weight_kg", label: "Weight", color: "#4D7C0F" },
];

const OVERVIEW_METRICS: MetricDef[] = [
  { key: "blood_pressure_systolic", label: "Systolic BP", color: "#14555A" },
  { key: "blood_pressure_diastolic", label: "Diastolic BP", color: "#2C7A7F" },
  { key: "blood_glucose_mg_dl", label: "Glucose", color: "#E2A63B" },
];

/**
 * Chart.js (via react-chartjs-2) is used here specifically — Recharts is
 * used elsewhere in the dashboards (see AlertSeverityChart, UsersByRoleChart)
 * so both libraries in the approved stack are genuinely exercised, not just
 * declared as dependencies.
 *
 * Shows every measurement a patient has logged. An "Overview" view plots the
 * three shared majors (BP + Glucose) together; selecting any other metric
 * plots that single measurement alone (they have very different units, so a
 * combined axis would be misleading).
 */
export function VitalsTrendChart({ readings }: VitalsTrendChartProps) {
  const [selected, setSelected] = useState<string>("overview");

  // Readings come back newest-first from the API; charts read left-to-right chronologically.
  const chronological = useMemo(() => [...readings].reverse(), [readings]);
  const labels = chronological.map((r) => new Date(r.recorded_at).toLocaleDateString());

  const activeMetrics = selected === "overview" ? OVERVIEW_METRICS : METRICS.filter((m) => m.key === selected);

  const data = {
    labels,
    datasets: activeMetrics.map((m) => ({
      label: m.label,
      data: chronological.map((r) => r[m.key] as number | null),
      borderColor: m.color,
      backgroundColor: m.color,
      tension: 0.3,
      spanGaps: true,
      pointRadius: 3,
    })),
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: "bottom" as const },
    },
    scales: {
      y: { beginAtZero: false },
    },
  };

  const chipClass = (active: boolean) =>
    `rounded-full px-3 py-1 text-xs font-medium transition-colors ${
      active ? "bg-teal-500 text-white" : "bg-surface-sunken text-ink-soft hover:bg-surface-border"
    }`;

  if (readings.length === 0) {
    return <p className="text-sm text-ink-soft">No vitals logged yet.</p>;
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        <button type="button" onClick={() => setSelected("overview")} className={chipClass(selected === "overview")}>
          Overview (BP + Glucose)
        </button>
        {METRICS.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => setSelected(m.key)}
            className={chipClass(selected === m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div className="mt-4">
        <Line data={data} options={options} />
      </div>
    </div>
  );
}