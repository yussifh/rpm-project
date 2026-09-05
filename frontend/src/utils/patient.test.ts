import { describe, expect, it, vi } from "vitest";
import { ageFromDateOfBirth, shortPatientRef } from "@/utils/patient";

describe("ageFromDateOfBirth", () => {
  it("computes age correctly when the birthday has already passed this year", () => {
    vi.setSystemTime(new Date("2026-08-05"));
    expect(ageFromDateOfBirth("1990-01-15")).toBe(36);
    vi.useRealTimers();
  });

  it("computes age correctly when the birthday hasn't happened yet this year", () => {
    vi.setSystemTime(new Date("2026-08-05"));
    expect(ageFromDateOfBirth("1990-12-25")).toBe(35);
    vi.useRealTimers();
  });

  it("handles the exact birthday (turns a year older today)", () => {
    vi.setSystemTime(new Date("2026-08-05"));
    expect(ageFromDateOfBirth("2000-08-05")).toBe(26);
    vi.useRealTimers();
  });

  it("handles the day before the birthday (hasn't turned older yet)", () => {
    vi.setSystemTime(new Date("2026-08-05"));
    expect(ageFromDateOfBirth("2000-08-06")).toBe(25);
    vi.useRealTimers();
  });
});

describe("shortPatientRef", () => {
  it("takes the first 8 characters, uppercased", () => {
    expect(shortPatientRef("a1b2c3d4-e5f6-7890-abcd-ef1234567890")).toBe("A1B2C3D4");
  });

  it("is stable for the same input (deterministic, not random)", () => {
    const id = "0f9e8d7c-1234-5678-9abc-def012345678";
    expect(shortPatientRef(id)).toBe(shortPatientRef(id));
  });
});
