from __future__ import annotations

from .config import load_scoring_config
from .models import (
    EvidenceRelationship,
    EvidenceScoreInput,
    EvidenceScoreResult,
    ScoringConfig,
    SupportStatus,
)

COMPONENT_NAMES = ("relevance", "entailment", "provenance", "independent_agreement")


def score_evidence(
    evidence: EvidenceScoreInput,
    config: ScoringConfig | None = None,
) -> EvidenceScoreResult:
    """Compute a bounded heuristic score and apply non-numeric safety overrides."""
    resolved = config or load_scoring_config()
    normalized: dict[str, float] = {}
    missing: list[str] = []
    overrides: list[str] = []

    for name in COMPONENT_NAMES:
        value = getattr(evidence.components, name)
        if value is None:
            missing.append(name)
            normalized[name] = resolved.missing_component_value
        else:
            normalized[name] = value

    if evidence.relationship is EvidenceRelationship.UNSUPPORTED:
        normalized["entailment"] = 0.0
        overrides.append("unsupported_relationship_zeroed_entailment")

    weights = resolved.weights
    score = sum(normalized[name] * getattr(weights, name) for name in COMPONENT_NAMES)
    score = round(min(1.0, max(0.0, score)), 6)

    if evidence.reliable_contradiction and resolved.reliable_contradiction_overrides_score:
        status = SupportStatus.CONTRADICTED
        overrides.append("reliable_contradiction")
    elif evidence.relationship is EvidenceRelationship.CONTRADICTS:
        status = SupportStatus.CONTRADICTED
        overrides.append("contradictory_relationship")
    elif (
        evidence.relationship is EvidenceRelationship.UNSUPPORTED
        and resolved.unsupported_relationship_forces_uncertain
    ):
        status = SupportStatus.UNCERTAIN
        overrides.append("unsupported_relationship_forced_uncertain")
    elif normalized["entailment"] == 0.0 and "entailment" in missing:
        status = SupportStatus.UNCERTAIN
        overrides.append("missing_entailment_forced_uncertain")
    elif score >= resolved.thresholds.supported:
        status = SupportStatus.SUPPORTED
    elif score >= resolved.thresholds.partial:
        status = SupportStatus.PARTIALLY_SUPPORTED
    else:
        status = SupportStatus.UNCERTAIN

    return EvidenceScoreResult(
        score_version=resolved.version,
        heuristic_score=score,
        support_status=status,
        normalized_components=normalized,
        missing_components=missing,
        overrides_applied=overrides,
        provisional=resolved.provisional,
    )
