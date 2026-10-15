from __future__ import annotations

from datetime import date

from .config import load_pricing_config
from .models import CostEstimate, PricingConfig, TokenUsage


def estimate_cost(
    usage: TokenUsage,
    model_id: str,
    as_of: date,
    config: PricingConfig | None = None,
) -> CostEstimate:
    resolved = config or load_pricing_config()
    if model_id not in resolved.models:
        raise ValueError(f"no pricing configured for model {model_id!r}")
    model = resolved.models[model_id]
    if as_of < model.effective_from or (
        model.effective_through is not None and as_of > model.effective_through
    ):
        raise ValueError(f"pricing for {model_id!r} is not valid on {as_of.isoformat()}")

    rates = model.per_million_tokens
    uncached_input = max(0, usage.input_tokens - usage.cached_input_tokens)
    input_cost = uncached_input * rates.input / 1_000_000
    cached_cost = usage.cached_input_tokens * rates.cached_input / 1_000_000
    output_cost = usage.output_tokens * rates.output_including_thinking / 1_000_000
    total = input_cost + cached_cost + output_cost

    return CostEstimate(
        model_id=model_id,
        pricing_version=resolved.version,
        currency=resolved.currency,
        input_cost=round(input_cost, 8),
        output_cost=round(output_cost, 8),
        cached_input_cost=round(cached_cost, 8),
        total_cost=round(total, 8),
    )
