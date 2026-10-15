# Bridge: Beyond Translation

**Understand more than words.** Bridge is an evidence-first system for explaining the language, humor, idioms, and cultural context in short-form video without hiding uncertainty.

This repository contains a tested local vertical slice for evidence-first short-video analysis plus the production foundation for claim-level scoring and reproducible evaluation. The UI and API deliberately show **No evaluation results yet** until a real benchmark run is supplied.

## What is implemented

- Versioned evidence scoring with configurable weights and provisional thresholds.
- Reliable-contradiction override and unsupported-relationship guardrails.
- Automatic and verified human-review metrics kept in separate schemas.
- Claim precision, grounded coverage, unsupported claim rate, abstention metrics, cultural-understanding ratings, paired baseline comparisons, latency, token use, and model-configured cost estimates.
- Sample sizes and 95% uncertainty intervals where meaningful.
- FastAPI endpoints for health, scoring, and evaluation aggregation.
- Responsive `/evaluation` dashboard with an honest empty state and methodology view.
- Responsive `/analyze` flow with real upload progress and live job states.
- Server-side MP4/MOV/WebM content checks, 100 MB and 120-second limits, SHA-256 hashing, private local files, and one-hour cleanup.
- Idempotent analysis jobs and structured Gemini Files API integration with citation-reference validation.
- Explicit, tested failure behavior when the Gemini key is missing; no fixture is substituted for live output.
- Unit tests covering every formula, missing labels, zero denominators, threshold boundaries, contradiction overrides, and cost calculations.

Not yet production-ready: jobs and records are process-local, storage is local rather than object storage, Gemini has not been exercised with a real credential in this environment, the curated retrieval corpus is absent, and feedback/reviewer/auth/deployment flows are not implemented. See [the audit](docs/AUDIT.md) and [living implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Repository layout

```text
apps/api/       FastAPI scoring and evaluation service
apps/web/       Next.js dashboard
config/         Versioned scoring and pricing configuration
docs/           Product, architecture, mathematics, and decisions
```

## Local setup

Requirements: Python 3.12+, Node.js 22+, npm 10+.

```bash
cp .env.example .env

cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
npm install
npm run dev:web
```

Open `http://localhost:3000/analyze` for the primary flow or `http://localhost:3000/evaluation` for metric reporting. The web app reads `NEXT_PUBLIC_API_URL`, which defaults to `http://localhost:8000`.

## Checks

```bash
npm run typecheck
npm run build

cd apps/api
pytest
ruff check .
mypy app
```

## Evaluation API

- `GET /api/v1/health`
- `GET /api/v1/evaluation/config`
- `GET /api/v1/evaluation/summary` — honest empty state until results are ingested
- `POST /api/v1/evaluation/score` — score one claim/evidence relationship
- `POST /api/v1/evaluation/aggregate` — aggregate provided evaluation cases

## Analysis API

- `POST /api/v1/uploads` — multipart upload with content, size, and duration validation
- `DELETE /api/v1/uploads/{upload_id}` — delete a local upload
- `POST /api/v1/analyses` — create an idempotent background analysis job
- `GET /api/v1/analyses/{analysis_id}` — read real stage, result, or failure state

`POST /api/v1/analyses` accepts an optional `Idempotency-Key` header. The current worker and record store are in-process; restarting the API loses job records. Local media is stored with owner-only permissions, expires after one hour while the process remains alive, and stale files are also purged before subsequent uploads. This is a development boundary, not a production storage claim.

For the exact definitions, missing-data policy, assumptions, and limitations, read [Mathematics and evaluation](docs/MATHEMATICS.md). The dashboard links to the same document.

## AI configuration

`GEMINI_MODEL` defaults to `gemini-3.8-flash`, the current Flash model documented by Google for multimodal video input. Model access must still be verified against the live Google AI account before the first inference. Pricing is not embedded in formulas: it is versioned in [`config/model-pricing.v1.json`](config/model-pricing.v1.json) and should be updated when the provider changes rates.

## Safety and privacy

Heuristic support scores are diagnostic values, not empirical probabilities. Bridge never renders them as a “confidence percentage.” Human-evaluation metrics require verified reference labels. The local slice requires disclosure before sending media to Gemini and uses private temporary files; production still requires durable private object storage and enforceable retention.

## Documentation

- [Mathematics and evaluation](docs/MATHEMATICS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decision log](docs/DECISIONS.md)
- [Model evaluation](docs/MODEL_EVALUATION.md)
- [Implementation audit](docs/AUDIT.md)

## License

Copyright (c) 2026. All rights reserved until a project license is selected.
