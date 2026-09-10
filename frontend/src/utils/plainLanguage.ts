import type { RiskPrediction, DiseaseType, RiskLevel } from "@/types/prediction";

export const DISEASE_PLAIN_NAME: Record<DiseaseType, string> = {
  diabetes: "Diabetes",
  hypertension: "High blood pressure",
  stroke: "Stroke",
};

export const DISEASE_PLAIN_DESCRIPTION: Record<DiseaseType, string> = {
  diabetes: "blood sugar",
  hypertension: "blood pressure",
  stroke: "blood pressure",
};

/** A short, everyday phrase describing what a risk level means — never
 *  a diagnosis, always paired with the "this is a monitoring result,
 *  not a diagnosis" framing the rest of the app already uses. */
const RISK_NEXT_STEP: Record<RiskLevel, string> = {
  low: "Nothing urgent right now. Keep checking your readings on your normal schedule.",
  moderate: "There is something to keep an eye on. Check again soon, and carry on with the advice below.",
  high: "This needs your attention. Please log a reading again soon and talk to your clinic about it.",
  critical: "This is important. Please contact your clinic or emergency care as soon as you can.",
};

/** When a model's precision is low (it flags far more than it confirms),
 *  an urgent "contact emergency care now" call-to-action is alarmist and
 *  would erode trust — so we soften the wording to "worth getting
 *  checked" instead. This keeps the headline consistent with the
 *  ModelTrustNote shown alongside it. Threshold (0.3) matches the
 *  trust-note's "low confidence" bucket. */
const LOW_PRECISION_SOFTENED: Record<RiskLevel, string> = {
  low: RISK_NEXT_STEP.low,
  moderate: RISK_NEXT_STEP.moderate,
  high:
    "This model is not very reliable at spotting this condition, so don't panic — but please get this checked with your clinic soon.",
  critical:
    "This model flags many false alarms, so please don't act urgently on it alone — but do contact your clinic to get this checked.",
};

export function riskPlainMessage(prediction: RiskPrediction, precision?: number): string {
  const disease = DISEASE_PLAIN_NAME[prediction.disease_type];
  const lowConfidence = precision !== undefined && precision < 0.3;
  const nextStep = lowConfidence ? LOW_PRECISION_SOFTENED[prediction.risk_level] : RISK_NEXT_STEP[prediction.risk_level];
  return `Your ${disease} check shows a ${prediction.risk_level} level of concern. ${nextStep}`;
}

/** A friendly, headline-style phrase for the dashboard — e.g. "Your blood
 *  pressure level of concern is high." */
export function riskStatusPhrase(prediction: RiskPrediction): string {
  const disease = DISEASE_PLAIN_NAME[prediction.disease_type];
  return `${disease}`;
}
