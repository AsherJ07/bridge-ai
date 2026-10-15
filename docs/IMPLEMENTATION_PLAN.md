# Living implementation plan

Last updated: 2026-10-14

## Status legend

- `[x]` implemented and locally verified
- `[~]` implemented but full target-runtime verification remains
- `[ ]` not implemented

## Phase 1 — Foundation and evaluation mathematics

- [x] Inspect the connected repository and establish a monorepo layout.
- [x] Verify the current Gemini Flash model and Files API direction against official documentation.
- [x] Add versioned evidence-scoring and pricing configuration.
- [x] Implement deterministic scoring, overrides, evaluation metrics, uncertainty, and cost estimates.
- [x] Separate automatic metrics from verified human-review metrics in both API and UI.
- [x] Add a responsive evaluation dashboard with an honest empty state.
- [x] Add formula, edge-case, schema, and API tests.
- [x] Document formulas, assumptions, missing-data behavior, limitations, and versioning.
- [~] Run Python checks under the declared Python 3.12 target. The available local runtime is Python 3.11; CI targets 3.12.

## Phase 2 — Working analysis vertical slice

- [ ] Add PostgreSQL entities and Alembic migrations for media, jobs, transcripts, evidence, interpretations, feedback, and evaluation.
- [~] Implemented server-side MP4/MOV/WebM content, size, duration, and SHA-256 validation with private local temporary storage and bounded cleanup. Private object storage remains open.
- [~] Implemented idempotent in-process background jobs and real polled stages. Redis-backed durability and multi-worker safety remain open.
- [~] Implemented Gemini Files API upload, bounded preparation wait, structured multimodal response schema, and provider-file deletion request. Live-account execution remains unverified because no credential is available.
- [~] Model, prompt, pipeline, and usage metadata are returned in the job result. Durable persistence and measured latency remain open.

## Phase 3 — Grounding and product flow

- [ ] Build the curated, licensed reference corpus and multilingual retrieval.
- [ ] Implement claim-level evidence association, citation validation, independent verification, and abstention.
- [~] Upload, real processing states, structured results, timestamps, evidence links, and uncertainty UI are implemented. Feedback and grounded follow-up remain open.
- [ ] Add explicit sample mode backed by licensed fixtures; keep it visually distinct from live inference.

## Phase 4 — Evaluation and demo readiness

- [ ] Freeze at least 20 licensed evaluation cases across the proposed case categories.
- [ ] Build the meaningful same-model baseline and run paired evaluation.
- [ ] Add reviewer workflow, disagreement capture, adjudication, and per-language drilldowns.
- [ ] Run the full benchmark; never seed the dashboard with invented values.
- [ ] Add integration and Playwright coverage for the complete journey.
- [ ] Capture desktop/mobile screenshots and finalize the five-minute demo script.

## Active risks

1. No Gemini API credential is present, so live model access and an end-to-end clip run are not verified.
2. No licensed video fixtures or verified reviewer labels exist yet.
3. Hosting and private object-storage providers are not selected.
4. Evidence thresholds need selection on a held-out labeled set before any calibration claim.
5. Authentication, rate limiting, durable storage/jobs, and production retention enforcement are not implemented.
