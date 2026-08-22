import type { DashboardPayload, ScenarioResult, ViewId } from "@/lib/types";
import { findScenario, formatImpact, formatSacrificed, formatShare } from "@/lib/format";

const STEPS: Array<{ id: ViewId; n: number; title: string; note: string }> = [
  { id: "intake", n: 1, title: "Citizen intake", note: "Gemini structures a complaint. Funding is not decided here." },
  { id: "demand", n: 2, title: "Demand intelligence", note: "Clusters, density, deficit, and investment gap." },
  { id: "geospatial", n: 3, title: "Geospatial view", note: "Synthetic district layout of demand and projects." },
  { id: "simulator", n: 4, title: "Policy simulator", note: "₹60 Cr envelope. Switch maximum impact vs 30% equity." },
  { id: "compare", n: 5, title: "Scenario comparison", note: "Who enters, who leaves, and the impact trade-off." },
  { id: "impact", n: 6, title: "Impact tracking", note: "P001 and P003 predicted vs observed. Not causal." },
  { id: "brics", n: 7, title: "BRICS / DPG", note: "Shared contracts; raw citizen data stays local." },
];

export default function DemoGuide({
  data,
  view,
  onGo,
  onClose,
}: {
  data: DashboardPayload | null;
  view: ViewId;
  onGo: (view: ViewId) => void;
  onClose: () => void;
}) {
  const baseline = data
    ? (findScenario(data.scenarios, 60, "maximum_impact") as ScenarioResult | undefined)
    : undefined;
  const equity = data
    ? (findScenario(data.scenarios, 60, "equity_30") as ScenarioResult | undefined)
    : undefined;

  return (
    <div className="demo-guide card">
      <div className="demo-guide-head">
        <div>
          <h3>Demo guide</h3>
          <p className="muted">
            Recommended walkthrough. Portfolio numbers come from the exported
            ₹60 Cr scenarios, not from hardcoded UI values.
          </p>
        </div>
        <button type="button" className="preset-btn" onClick={onClose}>
          Hide
        </button>
      </div>

      <ol className="demo-steps">
        {STEPS.map((step) => (
          <li key={step.id}>
            <button
              type="button"
              className={`demo-step ${view === step.id ? "active" : ""}`}
              onClick={() => onGo(step.id)}
            >
              <span className="demo-n">{step.n}</span>
              <span>
                <strong>{step.title}</strong>
                <span className="muted">{step.note}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>

      {baseline && equity ? (
        <div className="demo-tradeoff">
          <p>
            <strong>Primary demo · ₹{baseline.budget_cr} Cr</strong>
          </p>
          <p>
            Maximum impact: {baseline.selected_ids.join(" + ")} · impact{" "}
            {formatImpact(baseline.total_impact)} · underserved{" "}
            {formatShare(baseline.underserved_impact_share)}
          </p>
          <p>
            30% equity: {equity.selected_ids.join(" + ")} · impact{" "}
            {formatImpact(equity.total_impact)} · underserved{" "}
            {formatShare(equity.underserved_impact_share)}
          </p>
          <p className="muted">
            Trade-off: {formatSacrificed(equity.comparison_to_baseline.impact_sacrificed_pct)}{" "}
            aggregate impact sacrificed.
          </p>
        </div>
      ) : (
        <p className="muted">Load the dashboard export to show the ₹60 Cr trade-off.</p>
      )}
    </div>
  );
}
