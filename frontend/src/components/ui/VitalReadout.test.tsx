import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { VitalReadout } from "@/components/ui/VitalReadout";

describe("VitalReadout", () => {
  it("renders the label, value, and unit", () => {
    render(<VitalReadout label="Heart Rate" value={72} unit="bpm" status="stable" />);

    expect(screen.getByText("Heart Rate")).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText("bpm")).toBeInTheDocument();
  });

  it("renders without a unit when none is provided", () => {
    render(<VitalReadout label="Score" value="0.73" status="warning" />);
    expect(screen.getByText("0.73")).toBeInTheDocument();
  });

  it("applies the critical color class for critical status", () => {
    render(<VitalReadout label="SpO2" value={85} unit="%" status="critical" />);
    const valueEl = screen.getByText("85");
    expect(valueEl.className).toContain("text-status-critical");
  });

  it("applies the stable color class for stable status", () => {
    render(<VitalReadout label="SpO2" value={98} unit="%" status="stable" />);
    const valueEl = screen.getByText("98");
    expect(valueEl.className).toContain("text-status-stable");
  });
});
