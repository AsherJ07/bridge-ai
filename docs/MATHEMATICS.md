# Mathematics and evaluation

Version: `evidence-score-v1.0.0`  
Status: provisional heuristic  
Last updated: 2026-10-14

This document defines Bridge's claim-level evidence score and evaluation metrics. The definitions are intentionally conservative: absent evidence does not become positive evidence, unverified labels do not enter human-evaluation results, and a high weighted score cannot overrule reliable contradictory evidence.

## 1. Evidence support heuristic

For claim (c) and its evidence bundle, Bridge computes:

\[
H(c)=0.30R+0.35E+0.20P+0.15A
\]

where every component is normalized to ([0,1]):

| Component | Weight | Measurement and normalization |
| --- | ---: | --- |
| Relevance (R) | 0.30 | How directly the evidence concerns the same phrase, event, referent, language, and cultural setting as the claim. A retrieval/verifier rubric produces a bounded value: 0 for unrelated, 0.5 for partial topical overlap, and 1 for a direct match. Intermediate values are allowed only when the rubric emits them. Similarity alone is not entailment. |
| Entailment (E) | 0.35 | Whether the evidence actually supports the claim. 0 means it does not support the claim; 0.5 means it supports only a limited portion or requires a clearly disclosed inference; 1 means it directly supports the complete claim. An `unsupported` relationship forces this value to 0 even if an upstream model emitted a positive number. |
| Provenance (P) | 0.20 | Source traceability and fitness for the claim: 0 for unknown/unverifiable provenance, 0.5 for identifiable but weak or indirect provenance, and 1 for a directly inspectable, appropriate source with a stable identifier and version. Authored references are not automatically treated as external corroboration. |
| Independent agreement (A) | 0.15 | Agreement from genuinely independent evidence groups. 0 means none; 0.5 means one independent corroborating group; 1 means two or more. Multiple excerpts from one source, repeated retrievals of the same document, or the generator agreeing with its own output do not count as independent. |

The default weights live in [`config/evidence-scoring.v1.json`](../config/evidence-scoring.v1.json). They must sum to 1.0. The stored value is named `heuristic_score`, never `confidence`, `probability`, or `accuracy`.

### Status thresholds

The initial decision thresholds are:

\[
\operatorname{status}(c)=
\begin{cases}
\text{SUPPORTED} & H(c) \ge 0.80 \\
\text{PARTIALLY\_SUPPORTED} & 0.55 \le H(c) < 0.80 \\
\text{UNCERTAIN} & H(c) < 0.55
\end{cases}
\]

These values are provisional product heuristics. They have not been selected on a held-out labeled calibration set. Changing them requires a new configuration version and a new evaluation run; historical results retain the version used at inference time.

### Non-numeric overrides

The following rules run after the weighted score and take precedence over it:

1. Any reliable contradictory evidence produces `CONTRADICTED`, even when (H(c)) is high.
2. An explicit `contradicts` relationship produces `CONTRADICTED`.
3. An `unsupported` relationship sets (E=0) and produces `UNCERTAIN` under v1.
4. Missing entailment sets (E=0) and produces `UNCERTAIN` under v1.

The raw heuristic remains stored for debugging when an override applies, alongside `overrides_applied`. This makes the decision auditable without presenting the numeric value as the final truth.

### Missing evidence

Missing components receive 0 and weights are **not renormalized**. For example, if (R=1), (E=1), and both (P) and (A) are missing, then (H=0.65), not 1.0. Renormalization would make an incomplete bundle look fully supported. The API returns a `missing_components` list so callers can distinguish an observed zero from missing input.

If the full evidence relationship is unsupported, Bridge does not synthesize a positive entailment score. The verifier input and its final normalized components are both retained so this guardrail is testable.

## 2. Evaluation populations

Metrics are divided into two groups.

### Automatically measured

These use system output or request telemetry and do not claim human correctness:

- dataset and claim counts;
- grounded coverage;
- abstention rate;
- system-flagged unsupported rate;
- mean, median, and p95 latency;
- input, cached-input, and output token usage;
- cost estimates from the selected, effective pricing configuration.

### Verified human review

These require reviewer-verified reference labels. A label supplied without `label_verified=true` is rejected by schema validation rather than silently included:

- supported-claim precision;
- unsupported claim rate;
- appropriate abstention recall;
- average cultural-understanding rating;
- paired baseline-versus-Bridge improvement.

Ordinary user feedback and unadjudicated reviewer notes are not reference labels. Missing labels are excluded from the relevant denominator and reported through the sample size; they are never converted to negative labels.

## 3. Metric definitions

### Claim precision

Let (S) be claims Bridge marks `SUPPORTED` that also have a verified reference label, and let (T \subseteq S) be those whose reference label is `SUPPORTED`:

\[
\operatorname{ClaimPrecision}=\frac{|T|}{|S|}
\]

Claims without verified labels and claims not predicted `SUPPORTED` do not enter this denominator. If (|S|=0), the result is unavailable (`null`), not zero.

### Grounded coverage

Let (C) be all generated claims and (G) those with at least one valid, resolvable evidence association whose identifier exists in the evidence bundle:

\[
\operatorname{GroundedCoverage}=\frac{|G|}{|C|}
\]

This is an automatic coverage metric. It says evidence is attached and valid; it does not say the evidence proves the claim. If no claims were generated, the result is unavailable.

### Unsupported claim rate

Among all claims with verified reference labels (L), count claims (U) that Bridge emitted positively (`SUPPORTED` or `PARTIALLY_SUPPORTED`) while the verified label is `UNSUPPORTED` or `CONTRADICTED`:

\[
\operatorname{UnsupportedClaimRate}=\frac{|U|}{|L|}
\]

This is a human-review metric. Separately, `system_flagged_unsupported_rate` reports the fraction of generated claims the system itself marked `UNCERTAIN` or `CONTRADICTED`; that operational signal must not be presented as the verified unsupported claim rate.

### Abstention rate

For evaluated cases (D), with (B) cases where Bridge abstains:

\[
\operatorname{AbstentionRate}=\frac{|B|}{|D|}
\]

This is automatic and measures behavior, not whether abstention was correct.

### Appropriate abstention recall

Let (N) be cases with a verified label saying the system should abstain, and (A \subseteq N) the cases where Bridge did abstain:

\[
\operatorname{AppropriateAbstentionRecall}=\frac{|A|}{|N|}
\]

If no verified positive abstention cases exist, the result is unavailable. Cases labeled as not requiring abstention are not part of recall; a future precision metric may measure unnecessary abstention.

### Average cultural-understanding rating

For (n) verified Bridge ratings (r_i \in [1,5]):

\[
\bar r=\frac{1}{n}\sum_{i=1}^{n}r_i
\]

The displayed sample size is the number of verified ratings, not the dataset size. Reviewer disagreement should be stored before adjudication; v1 aggregation accepts only the verified/adjudicated value and does not invent a consensus score.

### Paired baseline-versus-Bridge improvement

Only cases with both a verified baseline rating (b_i) and a verified Bridge rating (r_i) are included:

\[
\Delta=\frac{1}{n}\sum_{i=1}^{n}(r_i-b_i)
\]

Subtracting within each case controls for case difficulty better than subtracting two independently averaged populations. Unpaired ratings are excluded. A positive value favors Bridge on the 1–5 rubric; it is not a relative percentage improvement.

### Latency

Latency uses successful measured request durations in milliseconds. Bridge and baseline are summarized separately:

- mean: arithmetic mean;
- median: 50th percentile;
- p95: the R-7 linearly interpolated 95th percentile, equivalent to common NumPy/browser analytics behavior.

Failed or timed-out requests must be recorded separately rather than assigned zero latency. End-to-end and model-only latency must not be mixed in one series; the run configuration declares which clock is used.

### Token usage

Token totals are summed separately for:

- input tokens;
- cached input tokens (a subset of input tokens);
- output tokens, including thinking tokens when the provider bills them as output.

Missing usage metadata excludes that case from `sample_size`; it does not impute zero. The total fields are still zero when no usage samples exist, and the dashboard renders cost as unavailable because the usage sample size is zero.

### Cost estimate

For per-million rates (p_i), (p_c), and (p_o):

\[
\operatorname{Cost}=\frac{(I-C)p_i + Cp_c + Op_o}{1{,}000{,}000}
\]

where (I) is total input tokens, (C) is cached input tokens, and (O) is output tokens. The model ID, service tier, pricing version, currency, and effective dates come from [`config/model-pricing.v1.json`](../config/model-pricing.v1.json). Unknown models or dates outside the configured effective window fail closed. Cost is labeled **estimated** unless reconciled to actual billing records.

The current configuration records Google Gemini 3.8 Flash standard rates effective on 2026-10-14: USD 0.75 per million input tokens, USD 3.75 per million output tokens including thinking, and USD 0.075 per million cached-input tokens. Provider prices can change; updating the file requires a new pricing version.

## 4. Sample sizes and uncertainty

Every metric returns its effective sample size and denominator. Zero denominators produce `null` with an explicit reason.

- Proportions use a two-sided 95% Wilson score interval.
- Means and paired mean differences use a two-sided 95% normal-approximation interval based on the sample standard deviation, clipped to the possible scale (1–5 for ratings and −4–4 for paired differences).
- A single observation has a point estimate but no interval.

These intervals describe sampling uncertainty under their assumptions; they do not cover label error, dataset shift, model non-determinism, prompt selection, or cultural disagreement. With small or non-random samples, they should be read as descriptive bounds rather than population guarantees.

## 5. Calibration policy

Bridge does not render a probability calibration chart in v1. The support heuristic is not a probability and there is no held-out, labeled calibration dataset yet. A future calibration view requires:

1. frozen, representative cases;
2. verified binary or ordinal outcome labels;
3. a predeclared mapping from score to outcome;
4. held-out evaluation separate from threshold tuning;
5. bin counts and uncertainty shown with the chart.

Until those conditions are met, a reliability diagram would imply evidence the product does not have.

## 6. Versioning and reproducibility

Every stored score or evaluation run records:

- scoring configuration version;
- model ID and generation configuration;
- prompt and pipeline versions;
- dataset version and run date;
- pricing version and effective date;
- raw component values, missing components, and applied overrides;
- telemetry sample counts;
- reviewer-label verification status.

Changing a component rubric, weight, threshold, missing-data rule, contradiction rule, metric denominator, percentile method, or pricing rate requires a new version. Historical runs are not recomputed in place.

## 7. Known limitations

- The v1 evidence weights and thresholds are expert-chosen heuristics, not empirically calibrated.
- A valid citation can still be misleading; grounded coverage is not factual accuracy.
- Cultural-understanding ratings are subjective and depend on reviewer background and rubric training.
- Normal-approximation intervals can be optimistic for very small samples or bounded ratings.
- The implemented aggregate does not yet estimate inter-rater reliability or stratified uncertainty by language.
- Token-based estimates can differ from invoices because of provider rounding, non-token fees, tier changes, or unreported usage.
- Comparisons are causal only to the extent that baseline and Bridge use the same frozen cases, model family, output language, and comparable token budgets.

## 8. Implementation map

- Scoring: `apps/api/app/evaluation/scoring.py`
- Metrics: `apps/api/app/evaluation/metrics.py`
- Uncertainty and percentiles: `apps/api/app/evaluation/statistics.py`
- Pricing: `apps/api/app/evaluation/pricing.py`
- Schemas and label gates: `apps/api/app/evaluation/models.py`
- Tests: `apps/api/tests/`
