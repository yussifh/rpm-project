import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toChartData } from "./featureImportanceData";

const BAR_COLOR = "#0F766E"; // teal-700, matches the app's primary action color

interface FeatureImportanceChartProps {
  importances: Record<string, number>;
}

/** Horizontal bar chart of which vitals/factors most influence a given
 * disease model's risk score — this is what "explainable AI" looks like
 * for a Random Forest without needing a full SHAP integration: the model
 * already exposes per-feature importances, this just renders them. */
export function FeatureImportanceChart({ importances }: FeatureImportanceChartProps) {
  const data = toChartData(importances);

  if (data.length === 0) {
    return <p className="text-sm text-ink-soft">No feature-importance data available for this model.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E6E5" horizontal={false} />
        <XAxis type="number" unit="%" tick={{ fontSize: 11, fill: "#4B5D63" }} />
        <YAxis type="category" dataKey="feature" width={110} tick={{ fontSize: 12, fill: "#4B5D63" }} />
        <Tooltip formatter={(value: number) => [`${value}%`, "Relative importance"]} />
        <Bar dataKey="value" radius={[0, 6, 6, 0]}>
          {data.map((entry) => (
            <Cell key={entry.feature} fill={BAR_COLOR} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
