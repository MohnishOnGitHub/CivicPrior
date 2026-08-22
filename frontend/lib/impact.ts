export const IMPACT_DATA_URL = "/data/seed-impact-observations.json";

export type ImpactDirection = "lower_is_better" | "higher_is_better";

export type ImpactMetric = {
  metric_name: string;
  label: string;
  unit: string;
  direction: ImpactDirection;
  baseline: number;
  predicted_value: number;
  observed_value: number;
};

export type ImpactProject = {
  project_id: string;
  name: string;
  location: string;
  category: string;
  status: string;
  causal_claim: boolean;
  metrics: ImpactMetric[];
};

export type ImpactCatalog = {
  synthetic: boolean;
  disclaimer: string;
  projects: ImpactProject[];
};

export type MetricComparison = ImpactMetric & {
  predicted_delta: number;
  observed_delta: number;
  beat_prediction: boolean;
};

export async function loadImpactObservations(): Promise<ImpactCatalog> {
  const response = await fetch(IMPACT_DATA_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load ${IMPACT_DATA_URL} (${response.status}).`);
  }
  return (await response.json()) as ImpactCatalog;
}

export function compareMetric(metric: ImpactMetric): MetricComparison {
  const predictedDelta = metric.predicted_value - metric.baseline;
  const observedDelta = metric.observed_value - metric.baseline;
  const beatPrediction =
    metric.direction === "lower_is_better"
      ? metric.observed_value < metric.predicted_value
      : metric.observed_value > metric.predicted_value;

  return {
    ...metric,
    predicted_delta: predictedDelta,
    observed_delta: observedDelta,
    beat_prediction: beatPrediction,
  };
}

export function formatMetricValue(value: number, unit: string): string {
  const rounded = Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);
  return `${rounded} ${unit}`;
}

export function formatSigned(value: number, digits = 1): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}
