import type { DashboardPayload, ScenarioResult } from "@/lib/types";
import {
  formatCr,
  formatDelta,
  formatImpact,
  formatShare,
} from "@/lib/format";
import { CategoryMix } from "./MixBars";
import { ProjectTable } from "./ProjectTable";

export default function SimulatorPanel({
  data,
  budget,
  equityMode,
  scenario,
  baseline,
  onBudget,
  onEquityMode,
}: {
  data: DashboardPayload;
  budget: number;
  equityMode: string;
  scenario: ScenarioResult | undefined;
  baseline: ScenarioResult | undefined;
  onBudget: (budget: number) => void;
  onEquityMode: (mode: string) => void;
}) {
  const modes = [
    { id: "maximum_impact", label: "Maximum impact / no equity constraint" },
    { id: "equity_25", label: "25% underserved impact" },
    { id: "equity_30", label: "30% underserved impact" },
    { id: "equity_40", label: "40% underserved impact" },
  ];
  const isBaseline = equityMode === "maximum_impact";
  const diff = scenario?.comparison_to_baseline;
  const selectedCount = scenario?.selected.length ?? 0;

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Policy simulator</h2>
          <p>
            Portfolios come from the exported optimizer. Changing budget or
            equity mode selects a precomputed scenario.
          </p>
        </div>
      </div>

      <div className="controls">
        <label>
          Budget
          <select
            value={budget}
            onChange={(event) => onBudget(Number(event.target.value))}
          >
            {data.meta.available_budgets_cr.map((value) => (
              <option key={value} value={value}>
                {formatCr(value)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Equity mode
          <select
            value={equityMode}
            onChange={(event) => onEquityMode(event.target.value)}
          >
            {modes.map((mode) => (
              <option key={mode.id} value={mode.id}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!scenario ? (
        <p className="error">No exported scenario for this budget and equity mode.</p>
      ) : !scenario.feasible ? (
        <p className="error">
          Infeasible under this constraint.{" "}
          {scenario.infeasible_reasons.join(" ")}
        </p>
      ) : (
        <>
          <div className="kpis">
            <article className="card">
              <div className="label">Selected</div>
              <div className="value">
                {selectedCount} {selectedCount === 1 ? "project" : "projects"} selected
              </div>
            </article>
            <article className="card">
              <div className="label">Total cost</div>
              <div className="value">{formatCr(scenario.total_cost)}</div>
            </article>
            <article className="card">
              <div className="label">Unused budget</div>
              <div className="value">{formatCr(scenario.unused_budget)}</div>
            </article>
            <article className="card">
              <div className="label">Service impact</div>
              <div className="value">{formatImpact(scenario.total_impact)}</div>
              <div className="hint">Estimated people-equivalent service impact</div>
            </article>
            <article className="card">
              <div className="label">Underserved impact share</div>
              <div className="value">{formatShare(scenario.underserved_impact_share)}</div>
            </article>
          </div>

          {!isBaseline && diff ? (
            <div className="kpis">
              <article className="card">
                <div className="label">Impact change vs baseline</div>
                <div className="value">{formatDelta(diff.impact_delta)}</div>
              </article>
              <article className="card">
                <div className="label">Underserved impact change vs baseline</div>
                <div className="value">{formatDelta(diff.underserved_impact_delta)}</div>
              </article>
              <article className="card">
                <div className="label">Projects added</div>
                <div className="value">{diff.added.length}</div>
                <div className="hint">{diff.added.join(", ") || "none"}</div>
              </article>
              <article className="card">
                <div className="label">Projects removed</div>
                <div className="value">{diff.removed.length}</div>
                <div className="hint">{diff.removed.join(", ") || "none"}</div>
              </article>
            </div>
          ) : null}

          <div className="section card">
            <h3>Category mix</h3>
            <CategoryMix counts={scenario.category_counts} spend={scenario.category_spend} />
          </div>

          <div className="section">
            <h3>Selected projects</h3>
            <ProjectTable projects={scenario.selected} />
          </div>
        </>
      )}
    </section>
  );
}
