import type { CompactProject, ScenarioResult } from "@/lib/types";
import {
  formatCr,
  formatDelta,
  formatImpact,
  formatShare,
  tradeoffSentence,
} from "@/lib/format";
import { CategoryMix } from "./MixBars";
import { ProjectTable } from "./ProjectTable";

function named(projects: CompactProject[], ids: string[]): CompactProject[] {
  const byId = new Map(projects.map((project) => [project.id, project]));
  return ids
    .map((id) => byId.get(id))
    .filter((project): project is CompactProject => Boolean(project));
}

function Snapshot({
  title,
  scenario,
}: {
  title: string;
  scenario: ScenarioResult;
}) {
  return (
    <div className="card compare-snapshot">
      <h3>{title}</h3>
      <p className="muted">{scenario.label}</p>
      <dl className="snapshot-list">
        <div>
          <dt>Projects</dt>
          <dd>
            {scenario.selected.length} selected
          </dd>
        </div>
        <div>
          <dt>Service impact</dt>
          <dd>{formatImpact(scenario.total_impact)}</dd>
        </div>
        <div>
          <dt>Underserved impact share</dt>
          <dd>{formatShare(scenario.underserved_impact_share)}</dd>
        </div>
        <div>
          <dt>Budget used</dt>
          <dd>
            {formatCr(scenario.total_cost)}
            <span className="muted"> · unused {formatCr(scenario.unused_budget)}</span>
          </dd>
        </div>
      </dl>
      <CategoryMix counts={scenario.category_counts} spend={scenario.category_spend} />
    </div>
  );
}

export default function ComparePanel({
  baseline,
  selected,
}: {
  baseline: ScenarioResult | undefined;
  selected: ScenarioResult | undefined;
}) {
  if (!baseline || !selected) {
    return <p className="error">Scenario export missing for this comparison.</p>;
  }

  const diff = selected.comparison_to_baseline;
  const allProjects = [...selected.selected, ...selected.unselected];
  const added = named(allProjects, diff.added);
  const removed = named(
    [...baseline.selected, ...baseline.unselected],
    diff.removed,
  );
  const isBaseline = selected.equity_mode === "maximum_impact";

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Scenario comparison</h2>
          <p>
            Baseline is maximum impact at the same budget. The policy scenario
            follows the simulator controls.
          </p>
        </div>
      </div>

      {isBaseline ? (
        <div className="callout ok">
          Baseline selected — no equity constraint is active, so there is no
          trade-off against another portfolio.
        </div>
      ) : (
        <div className="callout tradeoff">
          {tradeoffSentence(diff)}
        </div>
      )}

      <div className="split compare-split">
        <Snapshot title="Baseline" scenario={baseline} />
        <Snapshot title="Selected policy" scenario={selected} />
      </div>

      {!isBaseline ? (
        <div className="kpis section">
          <article className="card">
            <div className="label">Impact change vs baseline</div>
            <div className="value">{formatDelta(diff.impact_delta)}</div>
            <div className="hint">Estimated people-equivalent service impact</div>
          </article>
          <article className="card">
            <div className="label">Underserved impact change vs baseline</div>
            <div className="value">{formatDelta(diff.underserved_impact_delta)}</div>
            <div className="hint">
              {formatShare(diff.underserved_impact_share_baseline)} →{" "}
              {formatShare(diff.underserved_impact_share_selected)}
            </div>
          </article>
          <article className="card">
            <div className="label">Projects added</div>
            <div className="value">{diff.added.length}</div>
          </article>
          <article className="card">
            <div className="label">Projects removed</div>
            <div className="value">{diff.removed.length}</div>
          </article>
          <article className="card">
            <div className="label">Budget used</div>
            <div className="value">
              {formatCr(diff.budget_used_baseline ?? 0)} →{" "}
              {formatCr(diff.budget_used_selected ?? 0)}
            </div>
            <div className="hint">
              unused {formatCr(diff.unused_budget_selected ?? 0)}
            </div>
          </article>
        </div>
      ) : null}

      <div className="section">
        <h3>Entered under the selected policy</h3>
        <ProjectTable projects={added} empty="No projects added versus baseline." />
      </div>
      <div className="section">
        <h3>Left versus baseline</h3>
        <ProjectTable projects={removed} empty="No projects removed versus baseline." />
      </div>
    </section>
  );
}
