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
import type { VitalReading } from "@/types/vitals";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface VitalsTrendChartProps {
  readings: VitalReading[];
}

/**
 * Chart.js (via react-chartjs-2) is used here specifically — Recharts is
 * used elsewhere in the dashboards (see AlertSeverityChart, UsersByRoleChart)
 * so both libraries in the approved stack are genuinely exercised, not just
 * declared as dependencies.
 */
export function VitalsTrendChart({ readings }: VitalsTrendChartProps) {
  // Readings come back newest-first from the API; charts read left-to-right chronologically.
  const chronological = [...readings].reverse();
  const labels = chronological.map((r) => new Date(r.recorded_at).toLocaleDateString());

  const data = {
    labels,
    datasets: [
      {
        label: "Systolic BP",
        data: chronological.map((r) => r.blood_pressure_systolic),
        borderColor: "#14555A",
        backgroundColor: "#14555A",
        tension: 0.3,
      },
      {
        label: "Diastolic BP",
        data: chronological.map((r) => r.blood_pressure_diastolic),
        borderColor: "#2C7A7F",
        backgroundColor: "#2C7A7F",
        tension: 0.3,
      },
      {
        label: "Glucose (mg/dL)",
        data: chronological.map((r) => r.blood_glucose_mg_dl),
        borderColor: "#E2A63B",
        backgroundColor: "#E2A63B",
        tension: 0.3,
      },
    ],
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

  if (readings.length === 0) {
    return <p className="text-sm text-ink-soft">No vitals logged yet.</p>;
  }

  return <Line data={data} options={options} />;
}
