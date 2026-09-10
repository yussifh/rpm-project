import { useModelPrecision } from "@/hooks/useModelPrecision";
import { riskPlainMessage } from "@/utils/plainLanguage";
import type { RiskPrediction } from "@/types/prediction";

interface RiskHeadlineProps {
  prediction: RiskPrediction;
}

/** Plain-language risk statement for a single prediction, adjusted to the
 *  model's reliability: low-precision models get a softened "worth
 *  getting checked" message instead of an alarmist "contact emergency
 *  now", keeping the headline consistent with the ModelTrustNote. */
export function RiskHeadline({ prediction }: RiskHeadlineProps) {
  const precision = useModelPrecision(prediction.disease_type);
  return <>{riskPlainMessage(prediction, precision)}</>;
}
