# Bridge: Beyond Translation

**Understand more than words.** Bridge is an evidence-first system for explaining the language, humor, idioms, and cultural context in short-form video without hiding uncertainty.

This repository currently contains the production foundation for claim-level evidence scoring and reproducible evaluation. It includes a versioned FastAPI metrics API, a Next.js evaluation dashboard, a Gemini pricing configuration, and formula-level tests. Live video analysis is the next implementation phase; the UI and API deliberately show **No evaluation results yet** until a real run is supplied.

## What is implemented

- Versioned evidence scoring with configurable weights and provisional thresholds.
- Reliable-contradiction override and unsupported-relationship guardrails.
- Automatic and verified human-review metrics kept in separate schemas.
- Claim precision, grounded coverage, unsupported claim rate, abstention metrics, cultural-understanding ratings, paired baseline comparisons, latency, token use, and model-configured cost estimates.
- Sample sizes and 95% uncertainty intervals where meaningful.
- FastAPI endpoints for health, scoring, and evaluation aggregation.
- Responsive `/evaluation` dashboard with an honest empty state and methodology view.
- Unit tests covering every formula, missing labels, zero denominators, threshold boundaries, contradiction overrides, and cost calculations.

Not yet implemented: media upload/storage, background analysis jobs, Gemini video inference, retrieval, persistence, reviewer workflow, and deployment. See [the living implementation plan](docs/IMPLEMENTATION_PLAN.md).

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

Open `http://localhost:3000/evaluation`. The web app reads `NEXT_PUBLIC_API_URL`, which defaults to `http://localhost:8000`.

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

For the exact definitions, missing-data policy, assumptions, and limitations, read [Mathematics and evaluation](docs/MATHEMATICS.md). The dashboard links to the same document.

## AI configuration

`GEMINI_MODEL` defaults to `gemini-3.8-flash`, the current Flash model documented by Google for multimodal video input. Model access must still be verified against the live Google AI account before the first inference. Pricing is not embedded in formulas: it is versioned in [`config/model-pricing.v1.json`](config/model-pricing.v1.json) and should be updated when the provider changes rates.

## Safety and privacy

Heuristic support scores are diagnostic values, not empirical probabilities. Bridge never renders them as a “confidence percentage.” Human-evaluation metrics require verified reference labels. Media must eventually be stored privately with bounded retention and is expected to be sent to a third-party AI provider only after explicit disclosure.

## Documentation

- [Mathematics and evaluation](docs/MATHEMATICS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decision log](docs/DECISIONS.md)
- [Model evaluation](docs/MODEL_EVALUATION.md)

## License

Copyright (c) 2026. All rights reserved until a project license is selected.
