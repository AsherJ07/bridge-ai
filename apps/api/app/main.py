from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analysis.routes import router as analysis_router
from .analysis.settings import load_analysis_settings
from .evaluation.config import load_pricing_config, load_scoring_config
from .evaluation.metrics import aggregate_evaluation
from .evaluation.models import (
    EvaluationBatch,
    EvaluationSummary,
    EvidenceScoreInput,
    EvidenceScoreResult,
)
from .evaluation.scoring import score_evidence

app = FastAPI(
    title="Bridge API",
    version="0.1.0",
    description="Evidence scoring and evaluation for Bridge: Beyond Translation.",
)
analysis_settings = load_analysis_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[analysis_settings.cors_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)
app.include_router(analysis_router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bridge-api"}


@app.get("/api/v1/evaluation/config")
def evaluation_config() -> dict[str, object]:
    scoring = load_scoring_config()
    pricing = load_pricing_config()
    return {
        "scoring": scoring.model_dump(mode="json"),
        "pricing_version": pricing.version,
        "pricing_models": list(pricing.models),
    }


@app.post("/api/v1/evaluation/score", response_model=EvidenceScoreResult)
def score_claim(payload: EvidenceScoreInput) -> EvidenceScoreResult:
    return score_evidence(payload)


@app.post("/api/v1/evaluation/aggregate", response_model=EvaluationSummary)
def aggregate(payload: EvaluationBatch) -> EvaluationSummary:
    return aggregate_evaluation(payload)


@app.get("/api/v1/evaluation/summary", response_model=EvaluationSummary)
def empty_summary() -> EvaluationSummary:
    return aggregate_evaluation(
        EvaluationBatch(
            run_id="none",
            model_id="gemini-3.8-flash",
            cases=[],
            pricing_as_of=date(2026, 10, 14),
        )
    )
