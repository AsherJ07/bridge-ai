# AI pipeline

## Model selection

The configured default is `gemini-3.8-flash`. As of 2026-10-14, Google's official model and video-understanding documentation identifies it as a current Flash model with multimodal video support and Files API examples. The intended Python SDK is `google-genai==1.47.0`.

The model ID remains configurable through `GEMINI_MODEL`. Production startup will verify availability against the live account instead of assuming documentation implies account access.

## Planned stages

1. Deterministic media validation and timestamp-preserving metadata extraction.
2. Structured multimodal extraction of transcript, visible cues, slang, references, and ambiguity.
3. Bounded multilingual retrieval from a curated and licensed corpus.
4. Grounded generation that separates literal meaning, interpretation, alternatives, and uncertainty.
5. Claim-level verification with explicit evidence relationships and contradictory evidence.
6. Deterministic scoring, citation validation, and abstention.

Prompts and response schemas will be versioned before the first live inference. Model calls are not implemented in the current slice, and no sample output is represented as live analysis.
