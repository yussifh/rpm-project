import { useAsyncData } from "@/hooks/useAsyncData";
import { modelInfoApi } from "@/services/modelInfoApi";
import type { DiseaseType } from "@/types/prediction";

/** Loads a model's precision so callers can phrase risk messaging that
 *  matches that model's reliability (a low-precision model shouldn't
 *  trigger alarmist "contact emergency now" wording). Falls back to
 *  undefined while loading / on error, which keeps existing phrasing. */
export function useModelPrecision(diseaseType: DiseaseType): number | undefined {
  const { data } = useAsyncData(() => modelInfoApi.get(diseaseType), [diseaseType]);
  return data?.metrics.precision;
}
