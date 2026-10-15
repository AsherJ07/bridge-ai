from __future__ import annotations

from collections.abc import Iterable, Sequence

from .models import (
    AutomaticMetrics,
    EvaluationBatch,
    EvaluationSummary,
    HumanReviewMetrics,
    LatencySummary,
    MetricValue,
    ReferenceSupportLabel,
    SupportStatus,
    TokenUsage,
    UsageSummary,
)
from .pricing import estimate_cost
from .statistics import latency_summary, mean_interval, safe_rate, wilson_interval


def _proportion_metric(numerator: int, denominator: int, unavailable: str) -> MetricValue:
    value = safe_rate(numerator, denominator)
    low, high = wilson_interval(numerator, denominator)
    return MetricValue(
        value=value,
        numerator=numerator,
        denominator=denominator,
        sample_size=denominator,
        ci95_low=low,
        ci95_high=high,
        unavailable_reason=unavailable if denominator == 0 else None,
    )


def _mean_metric(
    values: Sequence[float],
    unavailable: str,
    bounds: tuple[float, float],
) -> MetricValue:
    point, low, high = mean_interval(values)
    if low is not None:
        low = max(bounds[0], low)
    if high is not None:
        high = min(bounds[1], high)
    return MetricValue(
        value=point,
        denominator=len(values),
        sample_size=len(values),
        ci95_low=low,
        ci95_high=high,
        unavailable_reason=unavailable if not values else None,
    )


def _usage_summary(usages: Iterable[TokenUsage | None]) -> UsageSummary:
    present = [usage for usage in usages if usage is not None]
    return UsageSummary(
        sample_size=len(present),
        input_tokens=sum(usage.input_tokens for usage in present),
        output_tokens=sum(usage.output_tokens for usage in present),
        cached_input_tokens=sum(usage.cached_input_tokens for usage in present),
    )


def _latency(values: Sequence[float]) -> LatencySummary:
    mean_ms, median_ms, p95_ms = latency_summary(values)
    return LatencySummary(
        sample_size=len(values),
        mean_ms=mean_ms,
        median_ms=median_ms,
        p95_ms=p95_ms,
    )


def aggregate_evaluation(batch: EvaluationBatch) -> EvaluationSummary:
    claims = [claim for case in batch.cases for claim in case.claims]
    grounded = sum(claim.has_valid_evidence for claim in claims)
    abstentions = sum(case.bridge_abstained for case in batch.cases)
    system_flagged = sum(
        claim.predicted_status in {SupportStatus.UNCERTAIN, SupportStatus.CONTRADICTED}
        for claim in claims
    )

    predicted_supported_labeled = [
        claim
        for claim in claims
        if claim.label_verified and claim.predicted_status is SupportStatus.SUPPORTED
    ]
    true_supported = sum(
        claim.reference_label is ReferenceSupportLabel.SUPPORTED
        for claim in predicted_supported_labeled
    )

    all_labeled_claims = [claim for claim in claims if claim.label_verified]
    unsupported_claims = sum(
        claim.reference_label
        in {ReferenceSupportLabel.UNSUPPORTED, ReferenceSupportLabel.CONTRADICTED}
        and claim.predicted_status
        in {SupportStatus.SUPPORTED, SupportStatus.PARTIALLY_SUPPORTED}
        for claim in all_labeled_claims
    )

    abstention_positive_cases = [
        case
        for case in batch.cases
        if case.abstention_label_verified and case.reference_should_abstain is True
    ]
    appropriate_abstentions = sum(case.bridge_abstained for case in abstention_positive_cases)

    cultural_ratings = [
        case.bridge_review.cultural_understanding
        for case in batch.cases
        if case.review_labels_verified and case.bridge_review is not None
    ]
    paired_improvements = [
        case.bridge_review.cultural_understanding - case.baseline_review.cultural_understanding
        for case in batch.cases
        if case.review_labels_verified
        and case.bridge_review is not None
        and case.baseline_review is not None
    ]

    bridge_latencies = [
        case.bridge_latency_ms for case in batch.cases if case.bridge_latency_ms is not None
    ]
    baseline_latencies = [
        case.baseline_latency_ms for case in batch.cases if case.baseline_latency_ms is not None
    ]
    bridge_usage = _usage_summary(case.bridge_tokens for case in batch.cases)
    baseline_usage = _usage_summary(case.baseline_tokens for case in batch.cases)

    bridge_usage_total = TokenUsage(
        input_tokens=bridge_usage.input_tokens,
        output_tokens=bridge_usage.output_tokens,
        cached_input_tokens=bridge_usage.cached_input_tokens,
    )
    baseline_usage_total = TokenUsage(
        input_tokens=baseline_usage.input_tokens,
        output_tokens=baseline_usage.output_tokens,
        cached_input_tokens=baseline_usage.cached_input_tokens,
    )

    automatic = AutomaticMetrics(
        dataset_size=len(batch.cases),
        claim_count=len(claims),
        grounded_coverage=_proportion_metric(
            grounded, len(claims), "No generated claims were supplied."
        ),
        abstention_rate=_proportion_metric(
            abstentions, len(batch.cases), "No evaluation cases were supplied."
        ),
        system_flagged_unsupported_rate=_proportion_metric(
            system_flagged, len(claims), "No generated claims were supplied."
        ),
        bridge_latency=_latency(bridge_latencies),
        baseline_latency=_latency(baseline_latencies),
        bridge_tokens=bridge_usage,
        baseline_tokens=baseline_usage,
        bridge_cost=estimate_cost(bridge_usage_total, batch.model_id, batch.pricing_as_of),
        baseline_cost=estimate_cost(baseline_usage_total, batch.model_id, batch.pricing_as_of),
    )

    human_review = HumanReviewMetrics(
        claim_precision=_proportion_metric(
            true_supported,
            len(predicted_supported_labeled),
            "No verified labels exist for claims predicted supported.",
        ),
        unsupported_claim_rate=_proportion_metric(
            unsupported_claims,
            len(all_labeled_claims),
            "No verified claim labels were supplied.",
        ),
        appropriate_abstention_recall=_proportion_metric(
            appropriate_abstentions,
            len(abstention_positive_cases),
            "No verified cases requiring abstention were supplied.",
        ),
        average_cultural_understanding=_mean_metric(
            cultural_ratings,
            "No verified cultural-understanding ratings were supplied.",
            (1.0, 5.0),
        ),
        paired_bridge_improvement=_mean_metric(
            paired_improvements,
            "No verified paired baseline and Bridge ratings were supplied.",
            (-4.0, 4.0),
        ),
    )

    status = "no_results" if not batch.cases else "complete"
    return EvaluationSummary(
        run_id=batch.run_id,
        model_id=batch.model_id,
        status=status,
        automatic=automatic,
        human_review=human_review,
        caveats=[
            "Support scores are provisional heuristics, not calibrated probabilities.",
            "Human-review metrics include verified labels only.",
            (
                "95% intervals are Wilson intervals for rates and "
                "normal-approximation intervals for means."
            ),
            "Cost is an estimate from the versioned pricing configuration, not a billing record.",
        ],
    )
