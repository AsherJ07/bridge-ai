export type MetricValue = {
  value: number | null;
  numerator: number | null;
  denominator: number;
  sample_size: number;
  ci95_low: number | null;
  ci95_high: number | null;
  unavailable_reason: string | null;
};

export type LatencySummary = {
  sample_size: number;
  mean_ms: number | null;
  median_ms: number | null;
  p95_ms: number | null;
};

export type UsageSummary = {
  sample_size: number;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
};

export type CostEstimate = {
  total_cost: number;
  currency: string;
  pricing_version: string;
  is_estimate: true;
};

export type EvaluationSummary = {
  run_id: string;
  model_id: string;
  status: "no_results" | "complete";
  automatic: {
    dataset_size: number;
    claim_count: number;
    grounded_coverage: MetricValue;
    abstention_rate: MetricValue;
    system_flagged_unsupported_rate: MetricValue;
    bridge_latency: LatencySummary;
    baseline_latency: LatencySummary;
    bridge_tokens: UsageSummary;
    baseline_tokens: UsageSummary;
    bridge_cost: CostEstimate;
    baseline_cost: CostEstimate;
  };
  human_review: {
    claim_precision: MetricValue;
    unsupported_claim_rate: MetricValue;
    appropriate_abstention_recall: MetricValue;
    average_cultural_understanding: MetricValue;
    paired_bridge_improvement: MetricValue;
  };
  caveats: string[];
};

const unavailableMetric = (reason: string): MetricValue => ({
  value: null,
  numerator: null,
  denominator: 0,
  sample_size: 0,
  ci95_low: null,
  ci95_high: null,
  unavailable_reason: reason,
});

export const emptySummary: EvaluationSummary = {
  run_id: "none",
  model_id: "gemini-3.8-flash",
  status: "no_results",
  automatic: {
    dataset_size: 0,
    claim_count: 0,
    grounded_coverage: unavailableMetric("No generated claims were supplied."),
    abstention_rate: unavailableMetric("No evaluation cases were supplied."),
    system_flagged_unsupported_rate: unavailableMetric("No generated claims were supplied."),
    bridge_latency: { sample_size: 0, mean_ms: null, median_ms: null, p95_ms: null },
    baseline_latency: { sample_size: 0, mean_ms: null, median_ms: null, p95_ms: null },
    bridge_tokens: { sample_size: 0, input_tokens: 0, output_tokens: 0, cached_input_tokens: 0 },
    baseline_tokens: { sample_size: 0, input_tokens: 0, output_tokens: 0, cached_input_tokens: 0 },
    bridge_cost: { total_cost: 0, currency: "USD", pricing_version: "google-gemini-pricing-2026-10-14", is_estimate: true },
    baseline_cost: { total_cost: 0, currency: "USD", pricing_version: "google-gemini-pricing-2026-10-14", is_estimate: true },
  },
  human_review: {
    claim_precision: unavailableMetric("No verified labels exist for claims predicted supported."),
    unsupported_claim_rate: unavailableMetric("No verified claim labels were supplied."),
    appropriate_abstention_recall: unavailableMetric("No verified cases requiring abstention were supplied."),
    average_cultural_understanding: unavailableMetric("No verified cultural-understanding ratings were supplied."),
    paired_bridge_improvement: unavailableMetric("No verified paired baseline and Bridge ratings were supplied."),
  },
  caveats: ["Support scores are provisional heuristics, not calibrated probabilities."],
};

export async function getEvaluationSummary(): Promise<EvaluationSummary> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(`${baseUrl}/api/v1/evaluation/summary`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) return emptySummary;
    return (await response.json()) as EvaluationSummary;
  } catch {
    return emptySummary;
  }
}
