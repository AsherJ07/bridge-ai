# AI pipeline

## Model selection

The configured default is `gemini-3.8-flash`. As of 2026-10-14, Google's official model and video-understanding documentation identifies it as a current Flash model with multimodal video support and Files API examples. The intended Python SDK is `google-genai==1.47.0`.

The model ID remains configurable through `GEMINI_MODEL`. `GEMINI_FALLBACK_MODELS` is an ordered list used only when a model times out, is rate-limited, or reports capacity exhaustion. Results record the model actually used.

## Implemented paths

1. Deterministic media validation and timestamp-preserving metadata extraction.
2. Gemini Files API upload and bounded file-processing wait.
3. Structured multimodal extraction of transcript, video-local evidence, interpretation, tone, and ambiguity.
4. Schema validation that requires evidence IDs for non-uncertain interpretations and caveats for uncertain interpretations.
5. A deterministic guard that downgrades any positive claim supported only by unverified user context to `uncertain` with a caveat.
6. Provider-file deletion request and an explicit completed or failed result.
7. In the Vercel path, direct upload to private Blob, server-side streaming to Gemini, and best-effort Blob deletion.

The implemented prompt is `video-analysis.v1`. The local FastAPI workflow is `analysis-pipeline.v1`; the Vercel workflow is `vercel-blob.v1`. A licensed connectivity clip completed against the deployed route with fallback models; the final guarded build used `gemini-3.5-flash-lite`. These runs verify integration, not factual quality or benchmark performance. Unit/API tests use a clearly scoped fake analyzer to verify the local result contract; the product never falls back to that fake.

## Still planned

- Curated, licensed multilingual retrieval beyond evidence visible in the submitted clip.
- Independent claim verification and application of the deterministic support score to analysis output.
- Durable telemetry, retries, and provider-deletion reconciliation.
- Grounded follow-up questions.
