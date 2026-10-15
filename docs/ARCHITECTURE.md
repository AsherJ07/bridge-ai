# Architecture

## Current local slice

```text
Next.js /analyze + /evaluation
        │ upload, create/poll job, GET summary
        ▼
FastAPI API
        ├── media content/size/duration validation
        ├── process-local upload and idempotent job store
        ├── Gemini Files + structured generation adapter
        ├── result citation-reference validation
        ├── Pydantic label and configuration gates
        ├── deterministic evidence scoring
        ├── deterministic metric aggregation
        └── versioned JSON configuration
             ├── scoring weights and thresholds
             └── model pricing and effective dates
```

The scoring and aggregation modules are pure apart from explicit configuration loading. Analysis jobs run as FastAPI background tasks and are polled by the browser. This makes the local journey functional, but jobs and records are lost on restart and are not safe across multiple API workers.

## Current deployed slice

```text
Next.js on Vercel
        │ short-lived upload authorization
        ▼
Private Vercel Blob ──stream──► Gemini Files API
        ▲                              │
        │ direct browser upload        ▼
        └──────────────────── structured generation
                                       │
                                       ▼
                            schema + evidence guards
                                       │
                                       ▼
                            result + actual model/usage
```

The deployed route deletes the Gemini file and Blob object in a `finally` path. These operations are best-effort, so production still needs monitoring and a reconciliation process. Its rate limiter is process-local and therefore not a distributed abuse-control boundary.

## Target production request flow

1. The web app uploads validated media directly to private storage through a short-lived signed request.
2. FastAPI creates an idempotent analysis job.
3. A Redis-backed worker validates media, uploads it to Gemini Files API, and requests structured extraction.
4. Retrieval returns a bounded evidence bundle from the curated corpus.
5. Generation produces claim/evidence relationships; a separate verifier scores them.
6. Deterministic validation rejects missing evidence IDs, applies contradiction and abstention rules, then persists results.
7. The web app receives real state events and renders evidence, uncertainty, and feedback controls.

## Failure handling

AI and storage calls will use timeouts, bounded retry with jitter, idempotency keys, and explicit failed/partial states. A live failure will never be replaced with an unlabeled fixture response.
