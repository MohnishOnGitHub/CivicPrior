import type { DashboardPayload } from "@/lib/types";
import { formatCr } from "@/lib/format";

export default function DemandPanel({ data }: { data: DashboardPayload }) {
  return (
    <section>
      <div className="page-head">
        <div>
          <h2>Demand intelligence</h2>
          <p>
            Enriched demand clusters from the citizen-request pipeline. Spatial
            layout is in Geospatial view using demo coordinates only.
          </p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Geography</th>
              <th>Category</th>
              <th>Unique req.</th>
              <th>Req / 1,000</th>
              <th>Deficit</th>
              <th>Vulnerability</th>
              <th>Equity</th>
              <th>Urgency</th>
              <th>Active investment</th>
              <th>Inv. gap</th>
              <th>Project</th>
            </tr>
          </thead>
          <tbody>
            {data.clusters.map((cluster) => (
              <tr key={cluster.cluster_id}>
                <td>
                  {cluster.geography}
                  {cluster.urban_rural ? ` · ${cluster.urban_rural}` : ""}
                </td>
                <td>{cluster.category}</td>
                <td>{cluster.unique_request_count}</td>
                <td>{cluster.requests_per_1000_residents.toFixed(4)}</td>
                <td>{cluster.infrastructure_deficit_score.toFixed(0)}</td>
                <td>{cluster.vulnerability_index.toFixed(0)}</td>
                <td>{cluster.equity_index.toFixed(1)}</td>
                <td>{cluster.max_urgency}</td>
                <td>{formatCr(cluster.approved_or_active_investment_cr)}</td>
                <td>{cluster.investment_gap_score.toFixed(0)}</td>
                <td>{cluster.linked_project_id ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.unmatched_clusters.length > 0 ? (
        <p className="muted section">
          Demand without a candidate project:{" "}
          {data.unmatched_clusters
            .map(
              (cluster) =>
                `${cluster.location} ${cluster.category} (${cluster.request_ids.join(", ")})`,
            )
            .join("; ")}
          .
        </p>
      ) : null}
    </section>
  );
}
