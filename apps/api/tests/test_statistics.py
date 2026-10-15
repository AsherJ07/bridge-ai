from __future__ import annotations

import pytest

from app.evaluation.statistics import latency_summary, percentile, safe_rate, wilson_interval


def test_safe_rate_zero_denominator_is_missing_not_zero() -> None:
    assert safe_rate(0, 0) is None


def test_wilson_interval_zero_denominator_is_missing() -> None:
    assert wilson_interval(0, 0) == (None, None)


def test_wilson_interval_is_bounded() -> None:
    low, high = wilson_interval(8, 10)
    assert low is not None and high is not None
    assert 0 <= low < 0.8 < high <= 1


def test_percentile_uses_linear_interpolation() -> None:
    assert percentile([100, 200, 300, 400], 0.95) == pytest.approx(385)


def test_latency_mean_median_and_p95() -> None:
    mean_ms, median_ms, p95_ms = latency_summary([100, 200, 300, 400])
    assert mean_ms == 250
    assert median_ms == 250
    assert p95_ms == pytest.approx(385)


def test_empty_latency_is_all_missing() -> None:
    assert latency_summary([]) == (None, None, None)
