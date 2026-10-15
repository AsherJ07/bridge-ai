# Decision log

## 2026-10-14 — Missing evidence is not reweighted

Missing score components contribute zero and are listed explicitly. Renormalizing across available components would let a sparse evidence bundle receive a perfect score.

## 2026-10-14 — Contradictions are a rule, not another weighted feature

Reliable contradictory evidence overrides the heuristic and produces `CONTRADICTED`. A weighted average cannot safely express this asymmetry.

## 2026-10-14 — Unsupported relationships force abstention

An upstream positive entailment value is discarded when the relationship is `unsupported`. This prevents an inconsistent model response from fabricating support.

## 2026-10-14 — Human metrics require verified labels

Schemas reject human labels and ratings unless their verification flag is set. Ordinary feedback remains useful product data but is not ground truth.

## 2026-10-14 — Empty evaluation is a first-class product state

The dashboard ships with “No evaluation results yet,” not sample numbers. It is visually complete without pretending a benchmark was run.

## 2026-10-14 — Pricing is data, not formula code

Model rates and effective dates live in a versioned configuration file. Unknown models or dates fail closed so estimates cannot silently use stale rates.

## 2026-10-14 — Current model default

The default is `gemini-3.8-flash`, which official Google documentation identifies as a current Flash model supporting video input and the Files API. The live account must confirm access before production inference.
