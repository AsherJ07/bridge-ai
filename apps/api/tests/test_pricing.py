from __future__ import annotations

from datetime import date

import pytest

from app.evaluation.models import TokenUsage
from app.evaluation.pricing import estimate_cost


def test_cost_uses_actual_configured_model_rates() -> None:
    result = estimate_cost(
        TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000),
        "gemini-3.8-flash",
        date(2026, 10, 14),
    )
    assert result.input_cost == 0.75
    assert result.output_cost == 3.75
    assert result.total_cost == 4.50
    assert result.is_estimate is True


def test_cached_tokens_use_cached_rate_and_are_not_double_counted() -> None:
    result = estimate_cost(
        TokenUsage(
            input_tokens=1_000_000,
            cached_input_tokens=500_000,
            output_tokens=0,
        ),
        "gemini-3.8-flash",
        date(2026, 10, 14),
    )
    assert result.input_cost == 0.375
    assert result.cached_input_cost == 0.0375
    assert result.total_cost == 0.4125


def test_missing_model_pricing_fails_closed() -> None:
    with pytest.raises(ValueError, match="no pricing configured"):
        estimate_cost(TokenUsage(), "unknown-model", date(2026, 10, 14))


def test_expired_pricing_fails_closed() -> None:
    with pytest.raises(ValueError, match="not valid"):
        estimate_cost(TokenUsage(), "gemini-3.8-flash", date(2027, 1, 1))
