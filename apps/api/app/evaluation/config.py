from __future__ import annotations

import json
from pathlib import Path

from .models import PricingConfig, ScoringConfig

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SCORING_PATH = REPOSITORY_ROOT / "config" / "evidence-scoring.v1.json"
DEFAULT_PRICING_PATH = REPOSITORY_ROOT / "config" / "model-pricing.v1.json"


def load_scoring_config(path: Path = DEFAULT_SCORING_PATH) -> ScoringConfig:
    return ScoringConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_pricing_config(path: Path = DEFAULT_PRICING_PATH) -> PricingConfig:
    return PricingConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))
