import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FeatureImportanceChart } from "@/components/charts/FeatureImportanceChart";
import { toChartData } from "@/components/charts/featureImportanceData";

// Note: we deliberately test `toChartData` (the pure data transform)
// rather than asserting on Recharts' rendered SVG output. Recharts'
// ResponsiveContainer needs real layout dimensions to render its
// children, which jsdom doesn't provide without a ResizeObserver polyfill
// — asserting on chart-internal text here would be testing jsdom's
// limitations, not this component's behavior.

describe("toChartData", () => {
  it("converts importance fractions to rounded percentages", () => {
    const data = toChartData({ age: 0.4064 });
    expect(data).toEqual([{ feature: "Age", value: 40.6 }]);
  });

  it("maps known feature keys to human-readable labels", () => {
    const data = toChartData({ age: 0.4, glucose: 0.3, bmi: 0.3 });
    const labels = data.map((d) => d.feature);
    expect(labels).toContain("Age");
    expect(labels).toContain("Blood Glucose");
    expect(labels).toContain("BMI");
  });

  it("falls back to the raw key for unmapped feature names", () => {
    const data = toChartData({ some_unmapped_feature: 1.0 });
    expect(data[0].feature).toBe("some_unmapped_feature");
  });

  it("sorts descending by importance", () => {
    const data = toChartData({ age: 0.2, bmi: 0.5, glucose: 0.3 });
    expect(data.map((d) => d.feature)).toEqual(["BMI", "Blood Glucose", "Age"]);
  });

  it("returns an empty array for empty input", () => {
    expect(toChartData({})).toEqual([]);
  });
});

describe("FeatureImportanceChart", () => {
  it("shows a fallback message when there are no importances", () => {
    render(<FeatureImportanceChart importances={{}} />);
    expect(screen.getByText(/no feature-importance data available/i)).toBeInTheDocument();
  });
});
