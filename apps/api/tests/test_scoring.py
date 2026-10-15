from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.evaluation.config import load_scoring_config
from app.evaluation.models import (
    ComponentScores,
    EvidenceRelationship,
    EvidenceScoreInput,
    ScoringConfig,
    SupportStatus,
)
from app.evaluation.scoring import score_evidence


def evidence(
    *,
    relevance: float | None,
    entailment: float | None,
    provenance: float | None,
    agreement: float | None,
    relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTS,
    contradiction: bool = False,
) -> EvidenceScoreInput:
    return EvidenceScoreInput(
        components=ComponentScores(
            relevance=relevance,
            entailment=entailment,
            provenance=provenance,
            independent_agreement=agreement,
        ),
        relationship=relationship,
        reliable_contradiction=contradiction,
    )


def test_default_weights_and_thresholds_are_versioned() -> None:
    config = load_scoring_config()
    assert config.version == "evidence-score-v1.0.0"
    assert config.provisional is True
    assert config.weights.model_dump() == {
        "relevance": 0.30,
        "entailment": 0.35,
        "provenance": 0.20,
        "independent_agreement": 0.15,
    }
    assert config.thresholds.supported == 0.80
    assert config.thresholds.partial == 0.55


@pytest.mark.parametrize(
    ("entailment", "expected"),
    [
        (0.7, SupportStatus.SUPPORTED),
        (0.4, SupportStatus.PARTIALLY_SUPPORTED),
        (0.0, SupportStatus.PARTIALLY_SUPPORTED),
    ],
)
def test_status_is_determined_from_weighted_score(
    entailment: float, expected: SupportStatus
) -> None:
    result = score_evidence(
        evidence(
            relevance=1.0,
            entailment=entailment,
            provenance=1.0,
            agreement=1.0,
        )
    )
    assert result.support_status is expected


def test_exact_supported_boundary() -> None:
    result = score_evidence(
        evidence(relevance=0.8, entailment=0.8, provenance=0.8, agreement=0.8)
    )
    assert result.heuristic_score == 0.8
    assert result.support_status is SupportStatus.SUPPORTED


def test_exact_partial_boundary() -> None:
    result = score_evidence(
        evidence(relevance=0.55, entailment=0.55, provenance=0.55, agreement=0.55)
    )
    assert result.heuristic_score == 0.55
    assert result.support_status is SupportStatus.PARTIALLY_SUPPORTED


def test_below_partial_is_uncertain() -> None:
    result = score_evidence(
        evidence(relevance=0.549, entailment=0.549, provenance=0.549, agreement=0.549)
    )
    assert result.support_status is SupportStatus.UNCERTAIN


def test_missing_components_contribute_zero_without_reweighting() -> None:
    result = score_evidence(
        evidence(relevance=1.0, entailment=1.0, provenance=None, agreement=None)
    )
    assert result.heuristic_score == 0.65
    assert result.missing_components == ["provenance", "independent_agreement"]
    assert result.support_status is SupportStatus.PARTIALLY_SUPPORTED


def test_missing_entailment_forces_uncertain_even_when_other_components_are_high() -> None:
    result = score_evidence(
        evidence(relevance=1.0, entailment=None, provenance=1.0, agreement=1.0)
    )
    assert result.heuristic_score == 0.65
    assert result.support_status is SupportStatus.UNCERTAIN
    assert "missing_entailment_forced_uncertain" in result.overrides_applied


def test_unsupported_relationship_never_fabricates_positive_entailment() -> None:
    result = score_evidence(
        evidence(
            relevance=1.0,
            entailment=1.0,
            provenance=1.0,
            agreement=1.0,
            relationship=EvidenceRelationship.UNSUPPORTED,
        )
    )
    assert result.normalized_components["entailment"] == 0.0
    assert result.heuristic_score == 0.65
    assert result.support_status is SupportStatus.UNCERTAIN


def test_reliable_contradiction_overrides_perfect_score() -> None:
    result = score_evidence(
        evidence(
            relevance=1.0,
            entailment=1.0,
            provenance=1.0,
            agreement=1.0,
            contradiction=True,
        )
    )
    assert result.heuristic_score == 1.0
    assert result.support_status is SupportStatus.CONTRADICTED
    assert result.score_semantics == "heuristic_not_probability"


def test_contradictory_relationship_overrides_score_without_flag() -> None:
    result = score_evidence(
        evidence(
            relevance=0.9,
            entailment=0.9,
            provenance=0.9,
            agreement=0.9,
            relationship=EvidenceRelationship.CONTRADICTS,
        )
    )
    assert result.support_status is SupportStatus.CONTRADICTED


def test_component_bounds_are_validated() -> None:
    with pytest.raises(ValidationError):
        ComponentScores(relevance=1.01)


def test_weights_must_sum_to_one() -> None:
    config = load_scoring_config().model_dump()
    config["weights"]["relevance"] = 0.2
    with pytest.raises(ValidationError):
        ScoringConfig.model_validate(config)
