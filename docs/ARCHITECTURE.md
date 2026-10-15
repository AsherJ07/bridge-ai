# Architecture

## Current slice

```text
Next.js /evaluation
        │ GET summary
        ▼
FastAPI evaluation API
        ├── Pydantic label and configuration gates
        ├── deterministic evidence scoring
        ├── deterministic metric aggregation
        └── versioned JSON configuration
             ├── scoring weights and thresholds
             └── model pricing and effective dates
```

The scoring and aggregation modules are pure apart from explicit configuration loading. This keeps mathematical behavior unit-testable and reusable in asynchronous workers later.

## Planned request flow

1. The web app uploads validated media directly to private storage through a short-lived signed request.
2. FastAPI creates an idempotent analysis job.
3. A Redis-backed worker validates media, uploads it to Gemini Files API, and requests structured extraction.
4. Retrieval returns a bounded evidence bundle from the curated corpus.
5. Generation produces claim/evidence relationships; a separate verifier scores them.
6. Deterministic validation rejects missing evidence IDs, applies contradiction and abstention rules, then persists results.
7. The web app receives real state events and renders evidence, uncertainty, and feedback controls.

## Failure handling

AI and storage calls will use timeouts, bounded retry with jitter, idempotency keys, and explicit failed/partial states. A live failure will never be replaced with an unlabeled fixture response.
