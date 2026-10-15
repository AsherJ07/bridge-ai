from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import mean, median, stdev

Z_95 = 1.959963984540054


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def wilson_interval(successes: int, total: int) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None
    proportion = successes / total
    denominator = 1 + (Z_95**2 / total)
    center = (proportion + (Z_95**2 / (2 * total))) / denominator
    margin = (
        Z_95
        * math.sqrt((proportion * (1 - proportion) / total) + (Z_95**2 / (4 * total**2)))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def mean_interval(values: Sequence[float]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    point = mean(values)
    if len(values) == 1:
        return point, None, None
    margin = Z_95 * stdev(values) / math.sqrt(len(values))
    return point, point - margin, point + margin


def percentile(values: Sequence[float], percentile_value: float) -> float | None:
    """R-7/NumPy-style linearly interpolated percentile."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def latency_summary(values: Sequence[float]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    return mean(values), median(values), percentile(values, 0.95)
