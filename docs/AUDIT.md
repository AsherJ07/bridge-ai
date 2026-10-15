# Implementation audit

Last verified: 2026-10-14

This audit compares the repository to the master Bridge specification. “Verified” means the behavior was exercised by an automated test, production build, or browser inspection during this audit. It does not mean a production service or live model account was tested.

## End-to-end journey status

| Journey step | Status | Evidence and limitation |
| --- | --- | --- |
| Reach analysis from landing page | Verified | The primary CTA and navigation open `/analyze`; the production Next.js build includes the route. |
| Choose a short video | Verified UI | The responsive form accepts one MP4, MOV, or WebM and previews it locally. Browser file-picker automation was not used. |
| Enforce media limits | Verified | API tests cover file signatures, unverifiable duration, more than 120 seconds, supported types, randomized filenames, metadata, and SHA-256. A streaming 100 MB guard is implemented; the full 100 MB boundary was not allocated in tests. |
| Disclose third-party processing | Verified UI | Submission stays disabled until the user accepts the Gemini disclosure. |
| Upload with real progress | Implemented | XHR progress events drive upload percentage. Browser execution with a real video was not performed because no licensed fixture was supplied. |
| Create and observe an analysis job | Verified contract | Jobs are idempotent and expose real stages with no fabricated processing percentage. The worker is process-local, not durable. |
| Run Gemini video analysis | Blocked externally | The Files API and structured-generation adapter are implemented, but `GEMINI_API_KEY` is absent. No live model response or model availability claim was fabricated. |
| Fail honestly without model access | Verified | API and UI expose `AI_NOT_CONFIGURED`; no sample response is substituted. |
| Validate and show results | Verified contract | A fake analyzer is injected only in API tests to prove the transcript/evidence/interpretation schema and frontend contract. Unknown evidence IDs and unsupported positive claims are rejected. No live result was displayed. |
| View evaluation | Verified | Existing formula tests pass and the dashboard truthfully reports no results. |

## Completed functionality

- Versioned scoring weights, provisional thresholds, contradiction override, missing-evidence policy, and non-probability semantics.
- Automatic metrics separated from verified human-review metrics, including uncertainty and sample sizes.
- Pricing-configured token cost estimates.
- Upload validation and local private storage with one-hour in-process expiry plus stale-file cleanup on later uploads.
- Idempotent background analysis API and structured Gemini adapter.
- Responsive landing, analysis, result/error states, and evaluation pages.
- CI definitions for Python 3.12 and Node 22.

## Incomplete or blocked

- No credential was available, so live Gemini model access, latency, token accounting, provider behavior, and deletion were not observed.
- PostgreSQL entities/migrations, Redis workers, object storage, signed URLs, multi-worker idempotency, and durable retries are not implemented.
- Authentication, authorization, rate limiting, abuse controls, and an admin-only evaluation surface are not implemented.
- Curated external evidence retrieval and independent verifier scoring are not connected to analysis output. Current evidence is limited to the submitted video and optional user context.
- Feedback/corrections, reviewer adjudication, grounded follow-up questions, demo fixtures, and evaluation-run APIs are not implemented.
- The 20-case licensed benchmark and verified human labels do not exist, so no baseline-versus-Bridge improvement is reported.
- Deployment, monitoring, a retention cleanup service, and production secrets/storage configuration are not selected.

## Untested assumptions

- The configured `gemini-3.8-flash` model is available to the eventual Google account and accepts the Pydantic response schema used here.
- MOV/WebM variants outside the covered ISO-BMFF/EBML metadata structures may be valid but rejected when duration cannot be verified. Rejection is safer than bypassing the limit.
- Provider file deletion is best-effort in this local worker; a production deletion reconciliation queue is still required.
- The local environment only provides Python 3.11.14. Static checks and tests passed there; the declared and CI target remains Python 3.12+.

## Verification record

- Backend: `ruff check app tests` passed; strict `mypy app` passed; `48 passed` with `94%` total coverage.
- Frontend: ESLint passed; TypeScript passed; the Next.js production build completed and generated `/`, `/analyze`, and `/evaluation`.
- Browser: `/analyze` loaded successfully in the local in-app browser and its narrow responsive layout was visually inspected.
- Security dependency check: `npm audit --omit=dev` reported zero vulnerabilities.

The backend run emitted deprecation warnings from third-party Starlette/Google SDK code. Application-owned deprecated HTTP status aliases were removed during this audit.
