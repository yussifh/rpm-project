import { describe, expect, it } from "vitest";
import { statusForRange, statusForSpo2 } from "@/utils/vitalsStatus";

describe("statusForRange", () => {
  it("returns 'info' when value is null or undefined", () => {
    expect(statusForRange(null, 140, 180)).toBe("info");
    expect(statusForRange(undefined, 140, 180)).toBe("info");
  });

  it("returns 'stable' when value is below the warning threshold", () => {
    expect(statusForRange(115, 140, 180)).toBe("stable");
  });

  it("returns 'warning' when value is at or above the warning threshold", () => {
    expect(statusForRange(145, 140, 180)).toBe("warning");
    expect(statusForRange(140, 140, 180)).toBe("warning");
  });

  it("returns 'critical' when value is at or above the critical threshold", () => {
    expect(statusForRange(190, 140, 180)).toBe("critical");
    expect(statusForRange(180, 140, 180)).toBe("critical");
  });
});

describe("statusForSpo2", () => {
  it("returns 'info' when value is missing", () => {
    expect(statusForSpo2(undefined)).toBe("info");
  });

  it("returns 'stable' for normal oxygen saturation", () => {
    expect(statusForSpo2(98)).toBe("stable");
  });

  it("returns 'warning' for mildly low oxygen saturation", () => {
    expect(statusForSpo2(93)).toBe("warning");
  });

  it("returns 'critical' for severely low oxygen saturation", () => {
    expect(statusForSpo2(85)).toBe("critical");
  });

  it("treats lower values as worse, unlike statusForRange", () => {
    // Sanity check the inversion: 99% is better than 91%.
    expect(statusForSpo2(99)).toBe("stable");
    expect(statusForSpo2(91)).toBe("warning");
  });
});
