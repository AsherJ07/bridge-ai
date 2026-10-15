from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNCERTAIN = "uncertain"
    CONTRADICTED = "contradicted"


class EvidenceRelationship(StrEnum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    UNSUPPORTED = "unsupported"
    CONTRADICTS = "contradicts"


class ReferenceSupportLabel(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


class ScoringWeights(StrictModel):
    relevance: float = Field(ge=0, le=1)
    entailment: float = Field(ge=0, le=1)
    provenance: float = Field(ge=0, le=1)
    independent_agreement: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> ScoringWeights:
        total = sum(
            (
                self.relevance,
                self.entailment,
                self.provenance,
                self.independent_agreement,
            )
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError("scoring weights must sum to 1.0")
        return self


class ScoringThresholds(StrictModel):
    supported: float = Field(ge=0, le=1)
    partial: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def thresholds_are_ordered(self) -> ScoringThresholds:
        if self.partial >= self.supported:
            raise ValueError("partial threshold must be lower than supported threshold")
        return self


class ScoringConfig(StrictModel):
    version: str
    provisional: bool = True
    weights: ScoringWeights
    thresholds: ScoringThresholds
    missing_component_value: float = Field(default=0.0, ge=0, le=1)
    reliable_contradiction_overrides_score: bool = True
    unsupported_relationship_forces_uncertain: bool = True


class ComponentScores(StrictModel):
    relevance: float | None = Field(default=None, ge=0, le=1)
    entailment: float | None = Field(default=None, ge=0, le=1)
    provenance: float | None = Field(default=None, ge=0, le=1)
    independent_agreement: float | None = Field(default=None, ge=0, le=1)


class EvidenceScoreInput(StrictModel):
    components: ComponentScores
    relationship: EvidenceRelationship
    reliable_contradiction: bool = False


class EvidenceScoreResult(StrictModel):
    score_version: str
    heuristic_score: float = Field(ge=0, le=1)
    support_status: SupportStatus
    normalized_components: dict[str, float]
    missing_components: list[str]
    overrides_applied: list[str]
    provisional: bool
    score_semantics: str = "heuristic_not_probability"


class PricingRates(StrictModel):
    input: float = Field(ge=0)
    output_including_thinking: float = Field(ge=0)
    cached_input: float = Field(default=0, ge=0)


class ModelPricing(StrictModel):
    service_tier: str
    effective_from: date
    effective_through: date | None = None
    per_million_tokens: PricingRates


class PricingConfig(StrictModel):
    version: str
    currency: str
    source_url: str
    models: dict[str, ModelPricing]


class TokenUsage(StrictModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)


class CostEstimate(StrictModel):
    model_id: str
    pricing_version: str
    currency: str
    input_cost: float
    output_cost: float
    cached_input_cost: float
    total_cost: float
    is_estimate: bool = True


class ClaimEvaluation(StrictModel):
    claim_id: str
    predicted_status: SupportStatus
    has_valid_evidence: bool
    reference_label: ReferenceSupportLabel | None = None
    label_verified: bool = False

    @model_validator(mode="after")
    def unverified_labels_are_rejected(self) -> ClaimEvaluation:
        if self.reference_label is not None and not self.label_verified:
            raise ValueError("reference_label may only be supplied when label_verified is true")
        if self.label_verified and self.reference_label is None:
            raise ValueError("label_verified requires a reference_label")
        return self


class ReviewerRatings(StrictModel):
    cultural_understanding: float = Field(ge=1, le=5)


class EvaluationCase(StrictModel):
    case_id: str
    language: str
    claims: list[ClaimEvaluation] = Field(default_factory=list)
    bridge_abstained: bool
    reference_should_abstain: bool | None = None
    abstention_label_verified: bool = False
    bridge_review: ReviewerRatings | None = None
    baseline_review: ReviewerRatings | None = None
    review_labels_verified: bool = False
    bridge_latency_ms: float | None = Field(default=None, ge=0)
    baseline_latency_ms: float | None = Field(default=None, ge=0)
    bridge_tokens: TokenUsage | None = None
    baseline_tokens: TokenUsage | None = None

    @model_validator(mode="after")
    def verified_human_fields_are_consistent(self) -> EvaluationCase:
        if self.reference_should_abstain is not None and not self.abstention_label_verified:
            raise ValueError(
                "reference_should_abstain may only be supplied with a verified abstention label"
            )
        if self.abstention_label_verified and self.reference_should_abstain is None:
            raise ValueError("verified abstention labels require reference_should_abstain")
        has_reviews = self.bridge_review is not None or self.baseline_review is not None
        if has_reviews and not self.review_labels_verified:
            raise ValueError("human ratings must be verified before evaluation")
        if self.review_labels_verified and self.bridge_review is None:
            raise ValueError("verified review data requires a Bridge review")
        return self


class EvaluationBatch(StrictModel):
    run_id: str
    model_id: str
    cases: list[EvaluationCase] = Field(default_factory=list)
    pricing_as_of: date


class MetricValue(StrictModel):
    value: float | None
    numerator: float | None = None
    denominator: int
    sample_size: int
    ci95_low: float | None = None
    ci95_high: float | None = None
    unavailable_reason: str | None = None


class LatencySummary(StrictModel):
    sample_size: int
    mean_ms: float | None
    median_ms: float | None
    p95_ms: float | None


class UsageSummary(StrictModel):
    sample_size: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int


class AutomaticMetrics(StrictModel):
    dataset_size: int
    claim_count: int
    grounded_coverage: MetricValue
    abstention_rate: MetricValue
    system_flagged_unsupported_rate: MetricValue
    bridge_latency: LatencySummary
    baseline_latency: LatencySummary
    bridge_tokens: UsageSummary
    baseline_tokens: UsageSummary
    bridge_cost: CostEstimate
    baseline_cost: CostEstimate


class HumanReviewMetrics(StrictModel):
    claim_precision: MetricValue
    unsupported_claim_rate: MetricValue
    appropriate_abstention_recall: MetricValue
    average_cultural_understanding: MetricValue
    paired_bridge_improvement: MetricValue


class EvaluationSummary(StrictModel):
    run_id: str
    model_id: str
    status: str
    automatic: AutomaticMetrics
    human_review: HumanReviewMetrics
    caveats: list[str]
