from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.evaluation.metrics import aggregate_evaluation
from app.evaluation.models import (
    ClaimEvaluation,
    EvaluationBatch,
    EvaluationCase,
    ReferenceSupportLabel,
    ReviewerRatings,
    SupportStatus,
    TokenUsage,
)


def test_empty_batch_reports_unavailable_human_metrics() -> None:
    summary = aggregate_evaluation(
        EvaluationBatch(
            run_id="empty",
            model_id="gemini-3.8-flash",
            pricing_as_of=date(2026, 10, 14),
        )
    )
    assert summary.status == "no_results"
    assert summary.automatic.dataset_size == 0
    assert summary.automatic.grounded_coverage.value is None
    assert summary.human_review.claim_precision.value is None
    assert summary.human_review.claim_precision.sample_size == 0


def test_all_requested_formulas_on_verified_cases() -> None:
    cases = [
        EvaluationCase(
            case_id="one",
            language="ur",
            bridge_abstained=False,
            reference_should_abstain=False,
            abstention_label_verified=True,
            claims=[
                ClaimEvaluation(
                    claim_id="one-a",
                    predicted_status=SupportStatus.SUPPORTED,
                    has_valid_evidence=True,
                    reference_label=ReferenceSupportLabel.SUPPORTED,
                    label_verified=True,
                ),
                ClaimEvaluation(
                    claim_id="one-b",
                    predicted_status=SupportStatus.PARTIALLY_SUPPORTED,
                    has_valid_evidence=False,
                    reference_label=ReferenceSupportLabel.UNSUPPORTED,
                    label_verified=True,
                ),
            ],
            bridge_review=ReviewerRatings(cultural_understanding=5),
            baseline_review=ReviewerRatings(cultural_understanding=3),
            review_labels_verified=True,
            bridge_latency_ms=100,
            baseline_latency_ms=80,
            bridge_tokens=TokenUsage(input_tokens=1_000, output_tokens=200),
            baseline_tokens=TokenUsage(input_tokens=800, output_tokens=150),
        ),
        EvaluationCase(
            case_id="two",
            language="es",
            bridge_abstained=True,
            reference_should_abstain=True,
            abstention_label_verified=True,
            claims=[
                ClaimEvaluation(
                    claim_id="two-a",
                    predicted_status=SupportStatus.UNCERTAIN,
                    has_valid_evidence=True,
                    reference_label=ReferenceSupportLabel.UNSUPPORTED,
                    label_verified=True,
                ),
                ClaimEvaluation(
                    claim_id="two-b",
                    predicted_status=SupportStatus.SUPPORTED,
                    has_valid_evidence=True,
                    reference_label=ReferenceSupportLabel.UNSUPPORTED,
                    label_verified=True,
                ),
            ],
            bridge_review=ReviewerRatings(cultural_understanding=3),
            baseline_review=ReviewerRatings(cultural_understanding=2),
            review_labels_verified=True,
            bridge_latency_ms=300,
            baseline_latency_ms=120,
            bridge_tokens=TokenUsage(input_tokens=2_000, output_tokens=300),
            baseline_tokens=TokenUsage(input_tokens=1_500, output_tokens=250),
        ),
    ]
    summary = aggregate_evaluation(
        EvaluationBatch(
            run_id="verified",
            model_id="gemini-3.8-flash",
            cases=cases,
            pricing_as_of=date(2026, 10, 14),
        )
    )

    assert summary.status == "complete"
    assert summary.automatic.grounded_coverage.value == 0.75
    assert summary.automatic.abstention_rate.value == 0.5
    assert summary.automatic.system_flagged_unsupported_rate.value == 0.25
    assert summary.human_review.claim_precision.value == 0.5
    assert summary.human_review.unsupported_claim_rate.value == 0.5
    assert summary.human_review.appropriate_abstention_recall.value == 1.0
    assert summary.human_review.average_cultural_understanding.value == 4.0
    assert summary.human_review.paired_bridge_improvement.value == 1.5
    assert summary.automatic.bridge_latency.mean_ms == 200
    assert summary.automatic.bridge_latency.median_ms == 200
    assert summary.automatic.bridge_latency.p95_ms == pytest.approx(290)
    assert summary.automatic.bridge_tokens.input_tokens == 3_000
    assert summary.automatic.bridge_tokens.output_tokens == 500
    assert summary.automatic.bridge_cost.total_cost == pytest.approx(0.004125)


def test_claim_precision_denominator_is_predicted_supported_with_labels_only() -> None:
    summary = aggregate_evaluation(
        EvaluationBatch(
            run_id="labels",
            model_id="gemini-3.8-flash",
            pricing_as_of=date(2026, 10, 14),
            cases=[
                EvaluationCase(
                    case_id="case",
                    language="en",
                    bridge_abstained=False,
                    claims=[
                        ClaimEvaluation(
                            claim_id="a",
                            predicted_status=SupportStatus.SUPPORTED,
                            has_valid_evidence=True,
                        ),
                        ClaimEvaluation(
                            claim_id="b",
                            predicted_status=SupportStatus.SUPPORTED,
                            has_valid_evidence=True,
                            reference_label=ReferenceSupportLabel.SUPPORTED,
                            label_verified=True,
                        ),
                    ],
                )
            ],
        )
    )
    assert summary.human_review.claim_precision.value == 1.0
    assert summary.human_review.claim_precision.sample_size == 1


def test_unverified_reference_label_is_rejected() -> None:
    with pytest.raises(ValidationError, match="label_verified"):
        ClaimEvaluation(
            claim_id="bad",
            predicted_status=SupportStatus.SUPPORTED,
            has_valid_evidence=True,
            reference_label=ReferenceSupportLabel.SUPPORTED,
        )


def test_missing_review_labels_are_rejected() -> None:
    with pytest.raises(ValidationError, match="verified"):
        EvaluationCase(
            case_id="bad",
            language="hi",
            bridge_abstained=False,
            bridge_review=ReviewerRatings(cultural_understanding=5),
        )


def test_unpaired_review_is_excluded_from_improvement() -> None:
    summary = aggregate_evaluation(
        EvaluationBatch(
            run_id="unpaired",
            model_id="gemini-3.8-flash",
            pricing_as_of=date(2026, 10, 14),
            cases=[
                EvaluationCase(
                    case_id="case",
                    language="hi",
                    bridge_abstained=False,
                    bridge_review=ReviewerRatings(cultural_understanding=4),
                    review_labels_verified=True,
                )
            ],
        )
    )
    assert summary.human_review.average_cultural_understanding.value == 4
    assert summary.human_review.paired_bridge_improvement.value is None
    assert summary.human_review.paired_bridge_improvement.sample_size == 0
