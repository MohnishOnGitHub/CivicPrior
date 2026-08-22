export type Mix = Record<string, number>;

export type CompactProject = {
  id: string;
  name: string;
  category: string;
  location: string;
  cost_cr: number;
  equity: number;
  need_score: number;
  expected_impact: number;
  estimated_beneficiaries: number;
  underserved: boolean;
};

export type DemandCluster = {
  cluster_id: string;
  geography: string;
  geo_id: string;
  urban_rural: string | null;
  category: string;
  requested_intervention: string;
  unique_request_count: number;
  total_request_count: number;
  requests_per_1000_residents: number;
  infrastructure_deficit_score: number;
  vulnerability_index: number;
  remoteness_index: number;
  equity_index: number;
  max_urgency: string;
  approved_or_active_investment_cr: number;
  investment_gap_score: number;
  linked_project_id: string | null;
};

export type ScenarioComparison = {
  added: string[];
  removed: string[];
  impact_delta: number | null;
  impact_sacrificed_pct: number | null;
  underserved_impact_delta: number | null;
  underserved_impact_share_baseline: number | null;
  underserved_impact_share_selected: number | null;
  budget_used_baseline: number | null;
  budget_used_selected: number | null;
  unused_budget_selected: number | null;
  category_counts_baseline: Mix;
  category_counts_selected: Mix;
};

export type ScenarioResult = {
  id: string;
  budget_cr: number;
  equity_mode: string;
  min_underserved_impact_share: number;
  label: string;
  feasible: boolean;
  selected: CompactProject[];
  unselected: CompactProject[];
  selected_ids: string[];
  total_cost: number;
  unused_budget: number;
  total_impact: number;
  underserved_expected_impact: number;
  underserved_impact_share: number | null;
  underserved_ids_selected: string[];
  category_counts: Mix;
  category_spend: Mix;
  category_mix: string;
  high_need_total: number;
  high_need_selected_ids: string[];
  high_need_project_coverage_pct: number | null;
  infeasible_reasons: string[];
  comparison_to_baseline: ScenarioComparison;
};

export type DashboardPayload = {
  schema_version: string;
  synthetic: boolean;
  catalog: string;
  generated_by: string;
  meta: {
    synthetic: boolean;
    default_budget_cr: number;
    available_budgets_cr: number[];
    underserved_rule: string;
    underserved_percentile: number;
    underserved_equity_min: number;
    underserved_ids: string[];
    seed_projects_modified: boolean;
  };
  overview: {
    total_citizen_requests: number;
    unique_requests: number;
    duplicate_requests: number;
    demand_clusters: number;
    candidate_projects: number;
    policy_budget_cr: number;
    request_category_mix: Mix;
    cluster_category_mix: Mix;
    project_category_mix: Mix;
    project_category_cost_cr: Mix;
  };
  clusters: DemandCluster[];
  unmatched_clusters: Array<{
    cluster_id: string;
    request_ids: string[];
    category: string;
    location: string;
  }>;
  projects: CompactProject[];
  scenarios: ScenarioResult[];
};

export type ViewId =
  | "intake"
  | "overview"
  | "demand"
  | "simulator"
  | "geospatial"
  | "impact"
  | "compare"
  | "brics";
