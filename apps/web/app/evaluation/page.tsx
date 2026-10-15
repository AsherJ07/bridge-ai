import {
  ArrowUpRight,
  BadgeCheck,
  Braces,
  Clock3,
  Coins,
  FlaskConical,
  Info,
  ShieldAlert,
} from "lucide-react";
import { getEvaluationSummary, type MetricValue } from "@/lib/evaluation";

function formatRate(metric: MetricValue): string {
  return metric.value === null ? "—" : `${(metric.value * 100).toFixed(1)}%`;
}

function MetricCard({
  label,
  metric,
  accent = false,
  display = "rate",
}: {
  label: string;
  metric: MetricValue;
  accent?: boolean;
  display?: "rate" | "rating";
}) {
  const value = metric.value === null
    ? "—"
    : display === "rating"
      ? `${metric.value.toFixed(2)} / 5`
      : formatRate(metric);
  const interval = metric.ci95_low === null || metric.ci95_high === null
    ? `n=${metric.sample_size} · interval unavailable`
    : display === "rating"
      ? `n=${metric.sample_size} · 95% CI ${metric.ci95_low.toFixed(2)}–${metric.ci95_high.toFixed(2)}`
      : `n=${metric.sample_size} · 95% CI ${formatRate({ ...metric, value: metric.ci95_low })}–${formatRate({ ...metric, value: metric.ci95_high })}`;
  return (
    <article className={`metric-card${accent ? " accent" : ""}`}>
      <div className="metric-heading"><span>{label}</span><Info size={14} aria-hidden="true" /></div>
      <strong>{value}</strong>
      <p>
        {metric.value === null
          ? metric.unavailable_reason
          : interval}
      </p>
    </article>
  );
}

export default async function EvaluationPage() {
  const summary = await getEvaluationSummary();
  const noResults = summary.status === "no_results";
  const { automatic, human_review: human } = summary;

  return (
    <main className="evaluation-page">
      <section className="evaluation-head">
        <div>
          <p className="kicker"><i /> Developer workspace</p>
          <h1>Evaluation, without the theater.</h1>
          <p>Operational telemetry and verified human judgments stay separate, so an empty dataset looks empty.</p>
        </div>
        <div className="run-state">
          <span className={noResults ? "state-dot idle" : "state-dot"} />
          <div><small>Latest run</small><strong>{noResults ? "Not run" : summary.run_id}</strong></div>
        </div>
      </section>

      {noResults && (
        <section className="empty-banner" role="status">
          <div className="empty-icon"><FlaskConical size={22} /></div>
          <div>
            <strong>No evaluation results yet</strong>
            <p>Run the frozen benchmark and attach verified reviewer labels before publishing comparative claims.</p>
          </div>
          <code>POST /api/v1/evaluation/aggregate</code>
        </section>
      )}

      <section className="run-facts" aria-label="Run metadata">
        <div><span>Cases evaluated</span><strong>{automatic.dataset_size || "—"}</strong></div>
        <div><span>Claims scored</span><strong>{automatic.claim_count || "—"}</strong></div>
        <div><span>Model</span><strong>{summary.model_id}</strong></div>
        <div><span>Pricing</span><strong>{automatic.bridge_cost.pricing_version.replace("google-gemini-pricing-", "")}</strong></div>
      </section>

      <section className="metric-section" aria-labelledby="automatic-title">
        <div className="section-title-row">
          <div>
            <span className="section-number">01</span>
            <div><h2 id="automatic-title">Automatically measured</h2><p>Computed from pipeline output and request telemetry.</p></div>
          </div>
          <Braces size={20} aria-hidden="true" />
        </div>
        <div className="metric-grid three">
          <MetricCard label="Grounded coverage" metric={automatic.grounded_coverage} accent />
          <MetricCard label="Abstention rate" metric={automatic.abstention_rate} />
          <MetricCard label="System-flagged unsupported" metric={automatic.system_flagged_unsupported_rate} />
        </div>
        <div className="telemetry-grid">
          <article className="telemetry-card">
            <div className="telemetry-icon"><Clock3 size={18} /></div>
            <div className="telemetry-copy"><span>Bridge latency</span><strong>{automatic.bridge_latency.median_ms === null ? "—" : `${automatic.bridge_latency.median_ms.toFixed(0)} ms`}</strong><small>median · p95 {automatic.bridge_latency.p95_ms === null ? "—" : `${automatic.bridge_latency.p95_ms.toFixed(0)} ms`} · n={automatic.bridge_latency.sample_size}</small></div>
          </article>
          <article className="telemetry-card">
            <div className="telemetry-icon violet"><Coins size={18} /></div>
            <div className="telemetry-copy"><span>Estimated API cost</span><strong>{automatic.bridge_tokens.sample_size === 0 ? "—" : `$${automatic.bridge_cost.total_cost.toFixed(4)}`}</strong><small>{automatic.bridge_tokens.input_tokens.toLocaleString()} input · {automatic.bridge_tokens.output_tokens.toLocaleString()} output tokens</small></div>
          </article>
        </div>
      </section>

      <section className="metric-section" aria-labelledby="human-title">
        <div className="section-title-row">
          <div>
            <span className="section-number">02</span>
            <div><h2 id="human-title">Verified human review</h2><p>Unavailable unless a reviewer-verified reference label is present.</p></div>
          </div>
          <BadgeCheck size={20} aria-hidden="true" />
        </div>
        <div className="metric-grid">
          <MetricCard label="Supported-claim precision" metric={human.claim_precision} />
          <MetricCard label="Unsupported claim rate" metric={human.unsupported_claim_rate} />
          <MetricCard label="Appropriate abstention recall" metric={human.appropriate_abstention_recall} />
          <MetricCard label="Cultural understanding" metric={human.average_cultural_understanding} display="rating" />
        </div>
        <div className="comparison-row">
          <div><span>Paired baseline → Bridge improvement</span><strong>{human.paired_bridge_improvement.value === null ? "Awaiting paired reviews" : `${human.paired_bridge_improvement.value > 0 ? "+" : ""}${human.paired_bridge_improvement.value.toFixed(2)} points`}</strong></div>
          <p>
            {human.paired_bridge_improvement.value === null
              ? "Computed per case before averaging. Unpaired reviews are excluded."
              : `n=${human.paired_bridge_improvement.sample_size} · 95% CI ${human.paired_bridge_improvement.ci95_low?.toFixed(2) ?? "—"}–${human.paired_bridge_improvement.ci95_high?.toFixed(2) ?? "—"}`}
          </p>
        </div>
      </section>

      <section className="methodology-card">
        <div className="method-icon"><ShieldAlert size={20} /></div>
        <div>
          <h2>These scores are not probabilities.</h2>
          <p>The support score is a versioned decision heuristic. Reliable contradictory evidence overrides the numeric result, and missing components receive zero weight contribution.</p>
        </div>
        <a href="https://github.com/AsherJ07/bridge-ai/blob/main/docs/MATHEMATICS.md" target="_blank" rel="noreferrer">
          Read the mathematics <ArrowUpRight size={15} />
        </a>
      </section>
    </main>
  );
}
