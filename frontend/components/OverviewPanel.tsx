import type { DashboardPayload } from "@/lib/types";
import { formatCr, formatInt } from "@/lib/format";
import { CategoryMix, MixBars } from "./MixBars";

export default function OverviewPanel({ data }: { data: DashboardPayload }) {
  const { overview, meta } = data;
  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Overview</h2>
          <p>
            Frozen evidence-derived catalog. Policy budget shown is the default
            working envelope ({formatCr(overview.policy_budget_cr)}).
          </p>
        </div>
      </div>
      <div className="cards">
        <article className="card">
          <div className="label">Citizen requests</div>
          <div className="value">{formatInt(overview.total_citizen_requests)}</div>
          <div className="hint">all synthetic intake records</div>
        </article>
        <article className="card">
          <div className="label">Unique after dedup</div>
          <div className="value">{formatInt(overview.unique_requests)}</div>
          <div className="hint">{overview.duplicate_requests} exact duplicates removed</div>
        </article>
        <article className="card">
          <div className="label">Demand clusters</div>
          <div className="value">{formatInt(overview.demand_clusters)}</div>
          <div className="hint">geo + category + intervention</div>
        </article>
        <article className="card">
          <div className="label">Candidate projects</div>
          <div className="value">{formatInt(overview.candidate_projects)}</div>
          <div className="hint">joined to evidence clusters</div>
        </article>
        <article className="card">
          <div className="label">Current policy budget</div>
          <div className="value">{formatCr(overview.policy_budget_cr)}</div>
          <div className="hint">default simulator envelope</div>
        </article>
        <article className="card">
          <div className="label">Underserved projects</div>
          <div className="value">{meta.underserved_ids.length}</div>
          <div className="hint">
            equity ≥ {(meta.underserved_percentile * 100).toFixed(0)}th percentile
            ({meta.underserved_equity_min.toFixed(2)})
          </div>
        </article>
      </div>

      <div className="section card">
        <h3>Candidate project mix</h3>
        <CategoryMix
          counts={overview.project_category_mix}
          spend={overview.project_category_cost_cr}
        />
      </div>
      <div className="section card">
        <h3>Demand cluster mix</h3>
        <MixBars mix={overview.cluster_category_mix} />
      </div>
    </section>
  );
}
