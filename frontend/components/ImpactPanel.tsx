"use client";

import { useEffect, useState } from "react";
import {
  compareMetric,
  formatMetricValue,
  formatSigned,
  loadImpactObservations,
  type ImpactCatalog,
  type MetricComparison,
} from "@/lib/impact";

function barWidth(value: number, max: number): string {
  if (max <= 0) return "0%";
  return `${Math.max(8, Math.round((value / max) * 100))}%`;
}

function MetricRow({ metric }: { metric: MetricComparison }) {
  const max = Math.max(metric.baseline, metric.predicted_value, metric.observed_value);
  return (
    <article className="card impact-metric">
      <div className="impact-metric-head">
        <h4>{metric.label}</h4>
        <span className={`badge ${metric.beat_prediction ? "yes" : "no"}`}>
          {metric.beat_prediction ? "beat prediction" : "below prediction"}
        </span>
      </div>
      <div className="impact-bars">
        <div>
          <div className="label">Before / baseline</div>
          <div className="bar">
            <span className="baseline" style={{ width: barWidth(metric.baseline, max) }} />
          </div>
          <div className="value">{formatMetricValue(metric.baseline, metric.unit)}</div>
        </div>
        <div>
          <div className="label">Predicted</div>
          <div className="bar">
            <span className="predicted" style={{ width: barWidth(metric.predicted_value, max) }} />
          </div>
          <div className="value">
            {formatMetricValue(metric.predicted_value, metric.unit)}
            <span className="hint"> ({formatSigned(metric.predicted_delta)})</span>
          </div>
        </div>
        <div>
          <div className="label">Observed</div>
          <div className="bar">
            <span className="observed" style={{ width: barWidth(metric.observed_value, max) }} />
          </div>
          <div className="value">
            {formatMetricValue(metric.observed_value, metric.unit)}
            <span className="hint"> ({formatSigned(metric.observed_delta)})</span>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function ImpactPanel() {
  const [catalog, setCatalog] = useState<ImpactCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadImpactObservations()
      .then(setCatalog)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load impact observations.");
      });
  }, []);

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Impact tracking</h2>
          <p>
            Baseline, predicted, and observed service indicators for sample
            completed projects. This does not change allocation or scoring.
          </p>
        </div>
      </div>

      <div className="callout mock-note">
        Synthetic demo observations. CivicPrior compares predicted and observed
        change; it does not claim the project caused the change.
      </div>

      {error ? <p className="error">{error}</p> : null}
      {!catalog && !error ? <p className="muted">Loading impact observations…</p> : null}

      {catalog?.projects.map((project) => (
        <div key={project.project_id} className="section">
          <h3>
            {project.project_id} · {project.name}
          </h3>
          <p className="muted">
            {project.location} · {project.category} · {project.status.replace(/_/g, " ")} ·
            synthetic demonstration data
          </p>
          <div className="impact-grid">
            {project.metrics.map((metric) => (
              <MetricRow key={metric.metric_name} metric={compareMetric(metric)} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
