"""Export a v0.1 dashboard payload from the frozen CivicPrior decision pipeline.

Does not change scoring, demand, equity classification, impact, or optimizer
search. It only serializes existing pipeline outputs for the frontend.

Writes:
  data/dashboard-v01.json
  frontend/public/data/dashboard-v01.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent
SRC_DIR = PIPELINE_DIR.parent
REPO_ROOT = SRC_DIR.parent
FRONTEND_COPY = REPO_ROOT / "frontend" / "public" / "data" / "dashboard-v01.json"
DASHBOARD_PATH = REPO_ROOT / "data" / "dashboard-v01.json"

if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from optimizer import OptimizerError, Scenario, compare_to_baseline, select_portfolio
from project_evidence import (
    DEFAULT_DERIVED_UNDERSERVED_PERCENTILE,
    PipelineError,
    build_derived_project_dataset,
    classify_underserved_by_percentile,
    derive_equity,
    derived_projects_for_optimizer,
    join_projects_to_evidence,
    load_enriched_pipeline,
)
from scoring import DataError

from clustering import ClusterError
from schema import RequestError
from enrichment import EvidenceError


DEFAULT_BUDGET_CR = 60.0
AVAILABLE_BUDGETS_CR = (50.0, 60.0, 100.0)
EQUITY_MODES: tuple[tuple[str, float, str], ...] = (
    ("maximum_impact", 0.0, "Maximum impact / no equity constraint"),
    ("equity_25", 0.25, "25% underserved impact"),
    ("equity_30", 0.30, "30% underserved impact"),
    ("equity_40", 0.40, "40% underserved impact"),
)


def _mix(values: list[str]) -> dict[str, int]:
    counts = Counter(values)
    return {key: counts[key] for key in sorted(counts)}


def _compact_project(project: dict[str, Any], underserved_ids: set[str]) -> dict[str, Any]:
    return {
        "id": project["id"],
        "name": project["name"],
        "category": project["category"],
        "location": project["location"],
        "cost_cr": project["cost_cr"],
        "equity": project["equity"],
        "need_score": project["need_score"],
        "expected_impact": project["expected_impact"],
        "estimated_beneficiaries": project["estimated_beneficiaries"],
        "underserved": project["id"] in underserved_ids,
    }


def _portfolio_payload(
    result: dict[str, Any],
    baseline: dict[str, Any],
    *,
    budget_cr: float,
    equity_mode: str,
    min_share: float,
    label: str,
    underserved_ids: set[str],
) -> dict[str, Any]:
    diff = compare_to_baseline(result, baseline)
    coverage = result.get("high_need_project_coverage_pct")
    underserved_delta = None
    if result.get("feasible") and baseline.get("feasible"):
        underserved_delta = round(
            result["underserved_expected_impact"] - baseline["underserved_expected_impact"],
            2,
        )
    return {
        "id": f"{budget_cr:.0f}_{equity_mode}",
        "budget_cr": budget_cr,
        "equity_mode": equity_mode,
        "min_underserved_impact_share": min_share,
        "label": label,
        "feasible": bool(result.get("feasible")),
        "selected": [_compact_project(project, underserved_ids) for project in result["selected"]],
        "unselected": [
            _compact_project(project, underserved_ids) for project in result["unselected"]
        ],
        "selected_ids": [project["id"] for project in result["selected"]],
        "total_cost": result["total_cost"],
        "unused_budget": result["unused_budget"],
        "total_impact": result["total_impact"],
        "underserved_expected_impact": result["underserved_expected_impact"],
        "underserved_impact_share": result["underserved_impact_share"],
        "underserved_ids_selected": result["underserved_ids"],
        "category_counts": result["category_counts"],
        "category_spend": result["category_spend"],
        "category_mix": result["category_mix"],
        "high_need_total": result["high_need_total"],
        "high_need_selected_ids": result["high_need_selected_ids"],
        "high_need_project_coverage_pct": coverage,
        "infeasible_reasons": result.get("infeasible_reasons") or [],
        "comparison_to_baseline": {
            "added": diff["added"],
            "removed": diff["removed"],
            "impact_delta": diff["impact_delta"],
            "impact_sacrificed_pct": diff["impact_sacrificed_pct"],
            "underserved_impact_delta": underserved_delta,
            "underserved_impact_share_baseline": baseline.get("underserved_impact_share"),
            "underserved_impact_share_selected": result.get("underserved_impact_share"),
            "budget_used_baseline": baseline.get("total_cost"),
            "budget_used_selected": result.get("total_cost"),
            "unused_budget_selected": result.get("unused_budget"),
            "category_counts_baseline": baseline.get("category_counts") or {},
            "category_counts_selected": result.get("category_counts") or {},
        },
    }


def build_dashboard_payload() -> dict[str, Any]:
    loaded = load_enriched_pipeline()
    clustered = {
        "total_requests": None,
        "unique_request_count": None,
        "duplicate_request_count": None,
        "total_clusters": None,
        "clusters": loaded["clusters"],
    }
    # load_enriched_pipeline currently returns projects/clusters/enriched only.
    # Recompute request totals from the cluster list so the exporter stays
    # aligned with clustering.py without changing that module.
    clusters = loaded["clusters"]
    total_requests = sum(cluster["total_request_count"] for cluster in clusters)
    unique_requests = sum(cluster["unique_request_count"] for cluster in clusters)
    duplicate_requests = sum(cluster["duplicate_request_count"] for cluster in clusters)
    clustered["total_requests"] = total_requests
    clustered["unique_request_count"] = unique_requests
    clustered["duplicate_request_count"] = duplicate_requests
    clustered["total_clusters"] = len(clusters)

    join_result = join_projects_to_evidence(
        loaded["projects"],
        loaded["clusters"],
        loaded["enriched"],
    )
    dataset = build_derived_project_dataset(join_result)
    derived = derived_projects_for_optimizer(dataset)
    classification = classify_underserved_by_percentile(
        derived,
        DEFAULT_DERIVED_UNDERSERVED_PERCENTILE,
    )
    underserved_ids = set(classification["underserved_ids"])
    equity_min = float(classification["threshold"])
    project_by_cluster = {
        row["source_cluster_id"]: row["id"] for row in dataset["projects"]
    }

    demand_rows = []
    for row in loaded["enriched"]:
        demand_rows.append(
            {
                "cluster_id": row["cluster_id"],
                "geography": row["location_name"],
                "geo_id": row["geo_id"],
                "urban_rural": row.get("urban_rural"),
                "category": row["category"],
                "requested_intervention": row["requested_intervention"],
                "unique_request_count": row["unique_request_count"],
                "total_request_count": row["total_request_count"],
                "requests_per_1000_residents": row["requests_per_1000_residents"],
                "infrastructure_deficit_score": row["infrastructure_deficit_score"],
                "vulnerability_index": row["vulnerability_index"],
                "remoteness_index": row["remoteness_index"],
                "equity_index": derive_equity(row),
                "max_urgency": row["max_urgency"],
                "approved_or_active_investment_cr": row["approved_or_active_investment_cr"],
                "investment_gap_score": row["investment_gap_score"],
                "linked_project_id": project_by_cluster.get(row["cluster_id"]),
            }
        )
    demand_rows.sort(
        key=lambda item: (-item["requests_per_1000_residents"], item["cluster_id"])
    )

    projects = [
        {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "location": row["location"],
            "cost_cr": row["cost_cr"],
            "equity": row["equity_derived"],
            "need_score": row["need_score_derived"],
            "expected_impact": row["expected_impact_derived"],
            "estimated_beneficiaries": row["estimated_beneficiaries"],
            "source_cluster_id": row["source_cluster_id"],
            "underserved": row["id"] in underserved_ids,
            "synthetic": True,
        }
        for row in dataset["projects"]
    ]

    scenarios: list[dict[str, Any]] = []
    for budget in AVAILABLE_BUDGETS_CR:
        by_mode: dict[str, dict[str, Any]] = {}
        for mode, share, label in EQUITY_MODES:
            result = select_portfolio(
                derived,
                Scenario(
                    budget_cr=budget,
                    min_underserved_impact_share=share,
                    underserved_equity_min=equity_min,
                    name=label,
                ),
            )
            by_mode[mode] = result
        baseline = by_mode["maximum_impact"]
        for mode, share, label in EQUITY_MODES:
            scenarios.append(
                _portfolio_payload(
                    by_mode[mode],
                    baseline,
                    budget_cr=budget,
                    equity_mode=mode,
                    min_share=share,
                    label=label,
                    underserved_ids=underserved_ids,
                )
            )

    return {
        "schema_version": "v0.1",
        "synthetic": True,
        "catalog": "evidence_derived",
        "generated_by": "src/pipeline/export_dashboard.py",
        "meta": {
            "synthetic": True,
            "default_budget_cr": DEFAULT_BUDGET_CR,
            "available_budgets_cr": list(AVAILABLE_BUDGETS_CR),
            "underserved_rule": (
                "equity_derived >= 75th percentile of the 12-project derived catalog"
            ),
            "underserved_percentile": DEFAULT_DERIVED_UNDERSERVED_PERCENTILE,
            "underserved_equity_min": equity_min,
            "underserved_ids": sorted(underserved_ids),
            "seed_projects_modified": False,
        },
        "overview": {
            "total_citizen_requests": total_requests,
            "unique_requests": unique_requests,
            "duplicate_requests": duplicate_requests,
            "demand_clusters": clustered["total_clusters"],
            "candidate_projects": len(projects),
            "policy_budget_cr": DEFAULT_BUDGET_CR,
            "request_category_mix": _mix(
                [cluster["category"] for cluster in clusters for _ in cluster["request_ids"]]
            ),
            "cluster_category_mix": _mix([cluster["category"] for cluster in clusters]),
            "project_category_mix": _mix([project["category"] for project in projects]),
            "project_category_cost_cr": {
                category: round(
                    sum(p["cost_cr"] for p in projects if p["category"] == category),
                    2,
                )
                for category in sorted({project["category"] for project in projects})
            },
        },
        "clusters": demand_rows,
        "unmatched_clusters": dataset.get("unmatched_clusters") or [],
        "projects": projects,
        "scenarios": scenarios,
    }


def write_dashboard_payload(payload: dict[str, Any]) -> tuple[Path, Path]:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(text, encoding="utf-8")
    FRONTEND_COPY.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_COPY.write_text(text, encoding="utf-8")
    return DASHBOARD_PATH, FRONTEND_COPY


def main() -> int:
    try:
        payload = build_dashboard_payload()
        source, copy = write_dashboard_payload(payload)
    except (DataError, OptimizerError, PipelineError, ClusterError, RequestError, EvidenceError) as exc:
        print(f"CivicPrior dashboard export failed: {exc}", file=sys.stderr)
        return 1

    print("CivicPrior dashboard payload exported.")
    print(f"  {source.relative_to(REPO_ROOT)}")
    print(f"  {copy.relative_to(REPO_ROOT)}")
    print("Frontend should fetch /data/dashboard-v01.json; do not hard-code portfolios.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
