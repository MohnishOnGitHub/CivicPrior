"""Join demand clusters with synthetic geo, infrastructure, and investment evidence."""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path
from typing import Any

EVIDENCE_DIR = Path(__file__).resolve().parent
REQUESTS_DIR = EVIDENCE_DIR.parent / "requests"
if str(REQUESTS_DIR) not in sys.path:
    sys.path.insert(0, str(REQUESTS_DIR))

from clustering import ClusterError, cluster_requests
from mock_extractor import extract_seed_requests
from schema import RequestError

_SPEC = importlib.util.spec_from_file_location(
    "civicprior_evidence_schema",
    EVIDENCE_DIR / "schema.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Could not load evidence schema module")
evidence_schema = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(evidence_schema)

ACTIVE_INVESTMENT_STATUSES = evidence_schema.ACTIVE_INVESTMENT_STATUSES
DATA_ROOT = evidence_schema.REPO_ROOT
EvidenceError = evidence_schema.EvidenceError
investment_gap_score = evidence_schema.investment_gap_score
load_geo_profiles = evidence_schema.load_geo_profiles
load_infra_metrics = evidence_schema.load_infra_metrics
load_investment_plans = evidence_schema.load_investment_plans


ENRICHED_FIELDS: tuple[str, ...] = (
    "cluster_id",
    "geo_id",
    "category",
    "unique_request_count",
    "total_request_count",
    "requests_per_1000_residents",
    "infrastructure_deficit_score",
    "vulnerability_index",
    "remoteness_index",
    "approved_or_active_investment_cr",
    "investment_gap_score",
    "max_urgency",
    "avg_confidence",
)


def _active_investment_cr(
    plans: list[dict[str, Any]],
    geo_id: str,
    category: str,
) -> float:
    total = sum(
        plan["amount_cr"]
        for plan in plans
        if plan["geo_id"] == geo_id
        and plan["category"] == category
        and plan["status"] in ACTIVE_INVESTMENT_STATUSES
    )
    return round(total, 2)


def enrich_clusters(
    clusters: list[dict[str, Any]],
    geo_profiles: dict[str, dict[str, Any]],
    infra_metrics: dict[tuple[str, str], dict[str, Any]],
    investment_plans: list[dict[str, Any]],
) -> dict[str, Any]:
    missing: list[str] = []
    enriched: list[dict[str, Any]] = []

    for cluster in clusters:
        geo_id = cluster["geo_id"]
        category = cluster["category"]
        profile = geo_profiles.get(geo_id)
        metric = infra_metrics.get((geo_id, category))
        if profile is None:
            missing.append(f"{cluster['cluster_id']}: no geo profile for {geo_id}")
            continue
        if metric is None:
            missing.append(
                f"{cluster['cluster_id']}: no infrastructure metric for {geo_id}/{category}"
            )
            continue

        population = profile["population"]
        unique_count = cluster["unique_request_count"]
        density = round((unique_count / population) * 1000.0, 4)
        active_cr = _active_investment_cr(investment_plans, geo_id, category)
        matching_plans = [
            {
                "id": plan["id"],
                "project_name": plan["project_name"],
                "amount_cr": plan["amount_cr"],
                "status": plan["status"],
            }
            for plan in investment_plans
            if plan["geo_id"] == geo_id and plan["category"] == category
        ]
        row = {
            "cluster_id": cluster["cluster_id"],
            "geo_id": geo_id,
            "location_name": profile["location_name"],
            "urban_rural": profile["urban_rural"],
            "category": category,
            "requested_intervention": cluster["requested_intervention"],
            "unique_request_count": unique_count,
            "total_request_count": cluster["total_request_count"],
            "duplicate_request_count": cluster["duplicate_request_count"],
            "population": population,
            "requests_per_1000_residents": density,
            "infrastructure_deficit_score": metric["infrastructure_deficit_score"],
            "service_coverage_pct": metric["service_coverage_pct"],
            "service_quality_score": metric["service_quality_score"],
            "vulnerability_index": profile["vulnerability_index"],
            "remoteness_index": profile["remoteness_index"],
            "approved_or_active_investment_cr": active_cr,
            "investment_gap_score": investment_gap_score(active_cr),
            "matching_investment_plans": matching_plans,
            "max_urgency": cluster["max_urgency"],
            "avg_confidence": cluster["avg_confidence"],
            "synthetic": True,
        }
        missing_fields = [field for field in ENRICHED_FIELDS if field not in row]
        if missing_fields:
            raise EvidenceError(
                f"{cluster['cluster_id']}: missing enriched field(s): {', '.join(missing_fields)}"
            )
        enriched.append(row)

    if missing:
        raise EvidenceError("Missing evidence joins:\n  - " + "\n  - ".join(missing))

    enriched.sort(
        key=lambda row: (-row["requests_per_1000_residents"], row["cluster_id"])
    )
    return {
        "enriched_clusters": enriched,
        "missing_joins": [],
        "geo_profile_count": len(geo_profiles),
        "infra_metric_count": len(infra_metrics),
        "investment_plan_count": len(investment_plans),
    }


def _format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    if not rows:
        return "(none)"
    widths = [
        max(len(headers[col]), *(len(row[col]) for row in rows))
        for col in range(len(headers))
    ]
    header_line = "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    rule = "  ".join("-" * widths[i] for i in range(len(headers)))
    body = "\n".join(
        "  ".join(row[i].ljust(widths[i]) for i in range(len(headers)))
        for row in rows
    )
    return f"{header_line}\n{rule}\n{body}"


def _cluster_row(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        row["cluster_id"],
        row["location_name"],
        row["category"],
        str(row["unique_request_count"]),
        f"{row['requests_per_1000_residents']:.4f}",
        f"{row['infrastructure_deficit_score']:.0f}",
        f"{row['vulnerability_index']:.0f}",
        f"{row['investment_gap_score']:.0f}",
        f"₹{row['approved_or_active_investment_cr']:.0f}",
        row["max_urgency"],
    )


def print_report(result: dict[str, Any]) -> None:
    rows = result["enriched_clusters"]
    headers = (
        "Cluster",
        "Geo",
        "Category",
        "Unique",
        "Req/1000",
        "Deficit",
        "Vuln",
        "Inv gap",
        "Active Cr",
        "Max urgency",
    )
    no_active = [row for row in rows if row["approved_or_active_investment_cr"] <= 0]
    by_deficit = sorted(
        rows, key=lambda row: (-row["infrastructure_deficit_score"], row["cluster_id"])
    )
    by_vuln = sorted(
        rows, key=lambda row: (-row["vulnerability_index"], row["cluster_id"])
    )
    gap_counts = Counter(row["investment_gap_score"] for row in rows)

    print("CivicPrior — Evidence Enrichment (v0.1)")
    print(f"Source: {DATA_ROOT.joinpath('data').relative_to(DATA_ROOT)}")
    print("All geo, infrastructure, and investment records are synthetic demo evidence.")
    print("need_score is not computed in this phase.")
    print()
    print(f"Geo profiles:          {result['geo_profile_count']}")
    print(f"Infrastructure metrics: {result['infra_metric_count']}")
    print(f"Investment plans:      {result['investment_plan_count']}")
    print(f"Enriched clusters:     {len(rows)}")
    print("Missing joins:         none")
    print(
        "Investment-gap mix:    "
        + ", ".join(f"{score}={gap_counts[score]}" for score in sorted(gap_counts, reverse=True))
    )
    print()
    print("All enriched clusters (by request density)")
    print(_format_table(headers, [_cluster_row(row) for row in rows]))
    print()
    print("Top 5 by requests_per_1000_residents")
    print(_format_table(headers, [_cluster_row(row) for row in rows[:5]]))
    print()
    print("Top 5 by infrastructure_deficit_score")
    print(_format_table(headers, [_cluster_row(row) for row in by_deficit[:5]]))
    print()
    print("Highest vulnerability")
    print(_format_table(headers, [_cluster_row(row) for row in by_vuln[:5]]))
    print()
    print("Clusters with no approved/in_progress investment")
    print(_format_table(headers, [_cluster_row(row) for row in no_active]))


def main() -> int:
    try:
        clustered = cluster_requests(extract_seed_requests())
        result = enrich_clusters(
            clustered["clusters"],
            load_geo_profiles(),
            load_infra_metrics(),
            load_investment_plans(),
        )
    except (EvidenceError, ClusterError, RequestError) as exc:
        print(f"CivicPrior evidence enrichment failed: {exc}", file=sys.stderr)
        return 1

    print_report(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
