# AI pipeline

## Model selection

The configured default is `gemini-3.8-flash`. As of 2026-10-14, Google's official model and video-understanding documentation identifies it as a current Flash model with multimodal video support and Files API examples. The intended Python SDK is `google-genai==1.47.0`.

The model ID remains configurable through `GEMINI_MODEL`. Production startup will verify availability against the live account instead of assuming documentation implies account access.

## Implemented local vertical slice

1. Deterministic media validation and timestamp-preserving metadata extraction.
2. Gemini Files API upload and bounded file-processing wait.
3. Structured multimodal extraction of transcript, video-local evidence, interpretation, tone, and ambiguity.
4. Schema validation that requires evidence IDs for non-uncertain interpretations and caveats for uncertain interpretations.
5. Provider-file deletion request and an explicit completed or failed job result.

The implemented prompt is `video-analysis.v1`; the workflow is `analysis-pipeline.v1`. No live call was made during this audit because `GEMINI_API_KEY` was not configured. Unit/API tests use a clearly scoped fake analyzer to verify the result contract; the product never falls back to that fake.

## Still planned

- Curated, licensed multilingual retrieval beyond evidence visible in the submitted clip.
- Independent claim verification and application of the deterministic support score to analysis output.
- Durable telemetry, retries, and provider-deletion reconciliation.
- Grounded follow-up questions.
