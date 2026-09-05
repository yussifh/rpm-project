import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Alert } from "@/types/alert";

const SEVERITY_COLORS: Record<string, string> = {
  info: "#3C6E9C",
  warning: "#E2A63B",
  critical: "#C0463C",
};

interface AlertSeverityChartProps {
  alerts: Alert[];
}

export function AlertSeverityChart({ alerts }: AlertSeverityChartProps) {
  const counts = { info: 0, warning: 0, critical: 0 };
  for (const alert of alerts) counts[alert.severity] += 1;

  const data = [
    { severity: "Info", count: counts.info, fill: SEVERITY_COLORS.info },
    { severity: "Warning", count: counts.warning, fill: SEVERITY_COLORS.warning },
    { severity: "Critical", count: counts.critical, fill: SEVERITY_COLORS.critical },
  ];

  if (alerts.length === 0) {
    return <p className="text-sm text-ink-soft">No alerts to display.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E6E5" />
        <XAxis dataKey="severity" tick={{ fontSize: 12, fill: "#4B5D63" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#4B5D63" }} />
        <Tooltip />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.severity} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
