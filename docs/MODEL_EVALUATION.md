# Model evaluation

The authoritative formulas, label policy, uncertainty methods, and limitations are in [MATHEMATICS.md](MATHEMATICS.md).

## Baseline

The planned baseline uses the same frozen video, output language, Gemini model, generation settings, and comparable output-token budget as Bridge. Its prompt is:

> Translate the video and explain relevant cultural context.

It does not receive the curated retrieval corpus, structured evidence verifier, or explicit grounded-abstention rules.

## Current results

No evaluation results yet. No benchmark clip, verified reviewer label, or live Gemini run has been supplied. The application therefore reports unavailable metrics instead of placeholder values.

## Required run record

Each run will record its date, dataset version, split, model ID, prompt versions, pipeline version, generation settings, scoring version, pricing version, case failures, latencies, token usage, and paired case outputs. Final comparisons require a frozen held-out set and must include failed cases.
