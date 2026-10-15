# Implementation audit

Last verified: 2026-10-15

This audit compares the repository to the master Bridge specification. “Verified” means the behavior was exercised by an automated test, production build, browser inspection, or the explicitly described production smoke test. A connectivity smoke test is not treated as benchmark evidence.

## End-to-end journey status

| Journey step | Status | Evidence and limitation |
| --- | --- | --- |
| Reach analysis from landing page | Verified | The primary CTA and navigation open `/analyze`; the production Next.js build includes the route. |
| Choose a short video | Verified UI | The responsive form accepts one MP4, MOV, or WebM and previews it locally. Browser file-picker automation was not used. |
| Enforce media limits | Verified | API tests cover file signatures, unverifiable duration, more than 120 seconds, supported types, randomized filenames, metadata, and SHA-256. A streaming 100 MB guard is implemented; the full 100 MB boundary was not allocated in tests. |
| Disclose third-party processing | Verified UI | Submission stays disabled until the user accepts the Gemini disclosure. |
| Upload with real progress | Verified contract | The client upload library drives byte progress and uploads directly to private Vercel Blob, avoiding the serverless request-body limit. A real private upload completed; browser progress animation was not separately automated. |
| Create and observe an analysis job | Verified contract | Jobs are idempotent and expose real stages with no fabricated processing percentage. The worker is process-local, not durable. |
| Run Gemini video analysis | Verified smoke path | A licensed Big Buck Bunny clip completed through the deployed Vercel route, private Blob read, Gemini Files upload, structured generation, schema/reference validation, and cleanup. The final guarded build used `gemini-3.5-flash-lite` after capacity fallback and reported 6,353 total tokens. This is not a benchmark result. |
| Fail honestly without model access | Verified | API and UI expose `AI_NOT_CONFIGURED`; no sample response is substituted. |
| Validate and show results | Verified contract and live payload | The deployed route returned a schema-valid live result. Unknown evidence IDs and unsupported positive claims are rejected; claims supported only by unverified user context are downgraded to uncertain with a caveat. Full browser rendering of the live result was not automated. |
| View evaluation | Verified | Existing formula tests pass and the dashboard truthfully reports no results. |

## Completed functionality

- Versioned scoring weights, provisional thresholds, contradiction override, missing-evidence policy, and non-probability semantics.
- Automatic metrics separated from verified human-review metrics, including uncertainty and sample sizes.
- Pricing-configured token cost estimates.
- Upload validation and local private storage with one-hour in-process expiry plus stale-file cleanup on later uploads.
- Idempotent background analysis API and structured Gemini adapter.
- Responsive landing, analysis, result/error states, and evaluation pages.
- CI definitions for Python 3.12 and Node 22.
- Owner-private production demo deployed through Vercel with runtime secrets, private Blob storage, direct client upload, same-origin enforcement, content validation, best-effort per-instance rate limiting, and deletion requests for both provider files and Blob objects.

## Incomplete or blocked

- PostgreSQL entities/migrations, Redis workers, durable multi-worker idempotency, and durable retries are not implemented. Vercel Blob object storage and short-lived client upload authorization are implemented for the deployed path.
- The deployed demo is owner-private and has basic per-IP rate limiting. Product-level user accounts, roles, durable/distributed abuse controls, and an admin-only evaluation surface are not implemented.
- Curated external evidence retrieval and independent verifier scoring are not connected to analysis output. Current evidence is limited to the submitted video and optional user context.
- Feedback/corrections, reviewer adjudication, grounded follow-up questions, demo fixtures, and evaluation-run APIs are not implemented.
- The 20-case licensed benchmark and verified human labels do not exist, so no baseline-versus-Bridge improvement is reported.
- The demo is deployed with runtime secrets and private object storage, but production monitoring and a deletion/retention reconciliation service are not implemented.

## Untested assumptions

- Model capacity is variable. Higher-priority models returned capacity errors during testing; the ordered fallback chain completed with `gemini-3.6-flash` and `gemini-3.5-flash-lite` on separate runs. Availability during a future demo cannot be guaranteed.
- MOV/WebM variants outside the covered ISO-BMFF/EBML metadata structures may be valid but rejected when duration cannot be verified. Rejection is safer than bypassing the limit.
- Provider and Blob deletion are best-effort; a production deletion reconciliation queue is still required. The smoke store was confirmed empty after cleanup.
- The local environment only provides Python 3.11.14. Static checks and tests passed there; the declared and CI target remains Python 3.12+.

## Verification record

- Backend: `ruff check app tests` passed; strict `mypy app` passed; `48 passed` with `94%` total coverage.
- Frontend: ESLint passed; TypeScript passed; the Next.js production build completed and generated `/`, `/analyze`, and `/evaluation`.
- Browser: `/analyze` loaded successfully in the local in-app browser and its narrow responsive layout was visually inspected.
- Security dependency check: `npm audit --omit=dev` reported zero vulnerabilities.
- Deployment: the Vercel production deployment reached `Ready`; authenticated health returned configured status and the full hosted analysis smoke returned HTTP 200. Vercel Authentication remains enabled, so anonymous visitors still receive the platform sign-in gate.

The backend run emitted deprecation warnings from third-party Starlette/Google SDK code. Application-owned deprecated HTTP status aliases were removed during this audit.
