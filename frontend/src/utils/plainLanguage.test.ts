import { describe, expect, it } from "vitest";
import {
  DISEASE_PLAIN_NAME,
  riskPlainMessage,
  riskStatusPhrase,
} from "@/utils/plainLanguage";
import type { RiskPrediction } from "@/types/prediction";

function prediction(overrides: Partial<RiskPrediction> = {}): RiskPrediction {
  return {
    id: "p1",
    patient_id: "pt-1",
    source_vital_id: null,
    disease_type: "diabetes",
    risk_score: 0.74,
    risk_level: "high",
    model_version: "v1",
    data_source: "synthetic",
    input_features: {},
    reasons: [],
    recommendations: [],
    predicted_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("DISEASE_PLAIN_NAME", () => {
  it("maps technical disease codes to everyday names", () => {
    expect(DISEASE_PLAIN_NAME.diabetes).toBe("Diabetes");
    expect(DISEASE_PLAIN_NAME.hypertension).toBe("High blood pressure");
    expect(DISEASE_PLAIN_NAME.stroke).toBe("Stroke");
  });
});

describe("riskStatusPhrase", () => {
  it("returns the plain-language disease name", () => {
    expect(riskStatusPhrase(prediction())).toBe("Diabetes");
    expect(riskStatusPhrase(prediction({ disease_type: "hypertension" }))).toBe(
      "High blood pressure"
    );
  });
});

describe("riskPlainMessage", () => {
  it("includes the plain disease name", () => {
    const msg = riskPlainMessage(prediction({ disease_type: "hypertension" }));
    expect(msg).toContain("High blood pressure");
  });

  it("tells the patient what the risk level means", () => {
    expect(riskPlainMessage(prediction({ risk_level: "low" }))).toMatch(/Nothing urgent/);
    expect(riskPlainMessage(prediction({ risk_level: "moderate" }))).toMatch(/keep an eye on/);
    expect(riskPlainMessage(prediction({ risk_level: "high" }))).toMatch(/needs your attention/);
    expect(riskPlainMessage(prediction({ risk_level: "critical" }))).toMatch(/contact your clinic/);
  });

  it("never repeats the raw score", () => {
    expect(riskPlainMessage(prediction())).not.toContain("%");
  });

  it("softens 'critical' wording for a low-precision model", () => {
    const msg = riskPlainMessage(prediction({ risk_level: "critical" }), 0.12);
    expect(msg).not.toMatch(/contact your clinic or emergency care as soon as you can/);
    expect(msg).toMatch(/false alarms/);
    expect(msg).toMatch(/contact your clinic to get this checked/);
  });

  it("softens 'high' wording for a low-precision model", () => {
    const msg = riskPlainMessage(prediction({ risk_level: "high" }), 0.1);
    expect(msg).not.toMatch(/needs your attention/);
    expect(msg).toMatch(/not very reliable/);
  });

  it("keeps the urgent wording when precision is acceptable", () => {
    const msg = riskPlainMessage(prediction({ risk_level: "critical" }), 0.65);
    expect(msg).toMatch(/contact your clinic or emergency care as soon as you can/);
  });
});
