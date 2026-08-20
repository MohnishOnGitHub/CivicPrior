"""CivicPrior Phase 10: evidence-derived decision inputs vs seeded project values.

Does not overwrite seed-projects.json and does not change scoring or the optimizer.

citizen_demand_derived is documented below and printed before any comparison
table so the formula is not a hidden implementation detail.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent
SRC_DIR = PIPELINE_DIR.parent
REPO_ROOT = SRC_DIR.parent
REQUESTS_DIR = SRC_DIR / "requests"
EVIDENCE_DIR = SRC_DIR / "evidence"
DERIVED_DATA_PATH = REPO_ROOT / "data" / "derived-project-inputs.json"

if str(REQUESTS_DIR) not in sys.path:
    sys.path.insert(0, str(REQUESTS_DIR))
from clustering import ClusterError, cluster_requests
from mock_extractor import extract_seed_requests
from schema import GEO_CATALOG, RequestError

if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))
from enrichment import (
    EvidenceError,
    enrich_clusters,
    load_geo_profiles,
    load_infra_metrics,
    load_investment_plans,
)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from scoring import (
    DATA_PATH as PROJECTS_PATH,
    DataError,
    NEED_WEIGHTS,
    expected_impact,
    load_projects,
    need_contributions,
    need_score,
)


LOCATION_TO_GEO_ID: dict[str, str] = {
    name: geo_id for geo_id, name in GEO_CATALOG.items()
}

# Maps each seed project onto the clustering intervention enum.
PROJECT_INTERVENTIONS: dict[str, str] = {
    "P001": "water_distribution_upgrade",
    "P002": "urban_road_expansion",
    "P003": "rural_phc_expansion",
    "P004": "village_road_connectivity",
    "P005": "municipal_water_storage_expansion",
    "P006": "phc_renovation",
    "P007": "urban_flyover_improvement",
    "P008": "rural_drinking_water_pipeline",
    "P009": "community_health_subcentre",
    "P010": "main_road_resurfacing",
    "P011": "water_treatment_plant_upgrade",
    "P012": "district_phc_staffing_upgrade",
}

URGENCY_SCORE: dict[str, float] = {
    "low": 25.0,
    "medium": 50.0,
    "high": 75.0,
    "critical": 100.0,
}

# citizen_demand_derived components. Density uses a saturating curve so a
# 12k village cannot 10× a 90k block. Volume uses log unique counts with a
# fixed cap of 10 so extra copies stop mattering. Persistence is span of
# unique+duplicate timestamps over a 21-day horizon.
DEMAND_DENSITY_TAU = 0.10
DEMAND_VOLUME_CAP = 10.0
DEMAND_PERSISTENCE_DAYS = 21.0
DEMAND_WEIGHT_DENSITY = 0.35
DEMAND_WEIGHT_VOLUME = 0.30
DEMAND_WEIGHT_URGENCY = 0.20
DEMAND_WEIGHT_PERSISTENCE = 0.15

CITIZEN_DEMAND_FORMULA = """
citizen_demand_derived =
    0.35 * density_score
  + 0.30 * volume_score
  + 0.20 * urgency_score
  + 0.15 * persistence_score

density_score     = 100 * (1 - exp(-requests_per_1000 / 0.10))
volume_score      = 100 * log(1 + unique_request_count) / log(1 + 10)
urgency_score     = {low:25, medium:50, high:75, critical:100}[max_urgency]
persistence_score = 100 * min(1, span_days / 21)
span_days         = calendar days from cluster first_seen to last_seen

Why this is not raw requests_per_1000:
- Tiny places: density saturates (0.25/1000 ≈ 92, not a linear spike).
- Large places: volume and urgency still score even when per-capita density is low.
- Persistence rewards issues that keep arriving, not a one-day burst.
""".strip()

SAFE_COMPARE_FIELDS: tuple[tuple[str, str], ...] = (
    ("infrastructure_deficit", "infrastructure_deficit_derived"),
    ("equity", "equity_derived"),
    ("urgency", "urgency_derived"),
    ("investment_gap", "investment_gap_derived"),
)

# Derived underserved rule. Seeded catalogs keep optimizer default equity >= 85.
DEFAULT_DERIVED_UNDERSERVED_PERCENTILE = 0.75
SENSITIVITY_PERCENTILES: tuple[float, ...] = (0.70, 0.75, 0.80)


class PipelineError(Exception):
    """Project-to-evidence join failed."""


def inclusive_percentile(values: list[float], p: float) -> float:
    """Inclusive linear-interpolation percentile (PERCENTILE.INC / Hyndman-Fan type 7).

    For n catalog values, index = p * (n - 1). The result is interpolated
    between adjacent order statistics. Not chosen from a portfolio outcome.
    """
    if not values:
        raise PipelineError("Cannot compute a percentile from an empty catalog")
    if not 0.0 <= p <= 1.0:
        raise PipelineError(f"Percentile p must be in [0, 1], got {p}")
    ordered = sorted(float(value) for value in values)
    n = len(ordered)
    if n == 1:
        return round(ordered[0], 2)
    index = p * (n - 1)
    lo = int(index)
    hi = min(lo + 1, n - 1)
    frac = index - lo
    return round(ordered[lo] * (1.0 - frac) + ordered[hi] * frac, 2)


def classify_underserved_by_percentile(
    projects: list[dict[str, Any]],
    percentile: float = DEFAULT_DERIVED_UNDERSERVED_PERCENTILE,
    equity_field: str = "equity",
) -> dict[str, Any]:
    ordered = sorted(projects, key=lambda item: (float(item[equity_field]), item["id"]))
    values = [float(item[equity_field]) for item in ordered]
    threshold = inclusive_percentile(values, percentile)
    classified = [
        item for item in ordered if float(item[equity_field]) >= threshold
    ]
    return {
        "percentile": percentile,
        "threshold": threshold,
        "method": "inclusive_linear_interpolation",
        "catalog_size": len(projects),
        "sorted_equities": [
            {
                "id": item["id"],
                "name": item["name"],
                "equity": float(item[equity_field]),
                "underserved": float(item[equity_field]) >= threshold,
            }
            for item in ordered
        ],
        "underserved": classified,
        "underserved_ids": [item["id"] for item in classified],
    }


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _calendar_span_days(first_seen: str, last_seen: str) -> int:
    first = _parse_ts(first_seen).date()
    last = _parse_ts(last_seen).date()
    return max(0, (last - first).days)


def _clamp_score(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 2)


def derive_infrastructure_deficit(enriched: dict[str, Any]) -> float:
    return _clamp_score(float(enriched["infrastructure_deficit_score"]))


def derive_equity(enriched: dict[str, Any]) -> float:
    return _clamp_score(
        0.70 * float(enriched["vulnerability_index"])
        + 0.30 * float(enriched["remoteness_index"])
    )


def derive_urgency(max_urgency: str) -> float:
    if max_urgency not in URGENCY_SCORE:
        raise PipelineError(f"Unknown max_urgency {max_urgency!r}")
    return URGENCY_SCORE[max_urgency]


def derive_investment_gap(enriched: dict[str, Any]) -> float:
    return _clamp_score(float(enriched["investment_gap_score"]))


def derive_citizen_demand(cluster: dict[str, Any], enriched: dict[str, Any]) -> dict[str, float]:
    unique_count = float(enriched["unique_request_count"])
    density = float(enriched["requests_per_1000_residents"])
    urgency_score = derive_urgency(cluster["max_urgency"])
    span_days = _calendar_span_days(cluster["first_seen"], cluster["last_seen"])
    density_score = 100.0 * (1.0 - math.exp(-density / DEMAND_DENSITY_TAU))
    volume_score = 100.0 * math.log(1.0 + unique_count) / math.log(1.0 + DEMAND_VOLUME_CAP)
    persistence_score = 100.0 * min(1.0, max(0, span_days) / DEMAND_PERSISTENCE_DAYS)
    derived = (
        DEMAND_WEIGHT_DENSITY * density_score
        + DEMAND_WEIGHT_VOLUME * volume_score
        + DEMAND_WEIGHT_URGENCY * urgency_score
        + DEMAND_WEIGHT_PERSISTENCE * persistence_score
    )
    return {
        "density_score": round(density_score, 2),
        "volume_score": round(volume_score, 2),
        "urgency_score": urgency_score,
        "persistence_score": round(persistence_score, 2),
        "span_days": float(max(0, span_days)),
        "citizen_demand_derived": _clamp_score(derived),
    }


def load_enriched_pipeline() -> dict[str, Any]:
    clustered = cluster_requests(extract_seed_requests())
    enriched = enrich_clusters(
        clustered["clusters"],
        load_geo_profiles(),
        load_infra_metrics(),
        load_investment_plans(),
    )
    return {
        "projects": load_projects(PROJECTS_PATH),
        "clusters": clustered["clusters"],
        "enriched": enriched["enriched_clusters"],
    }


def join_projects_to_evidence(
    projects: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    enriched_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    clusters_by_id = {cluster["cluster_id"]: cluster for cluster in clusters}
    enriched_by_key = {
        (row["geo_id"], row["category"], row["requested_intervention"]): row
        for row in enriched_rows
    }
    joined: list[dict[str, Any]] = []
    missing_projects: list[dict[str, Any]] = []

    for project in projects:
        geo_id = LOCATION_TO_GEO_ID.get(project["location"])
        intervention = PROJECT_INTERVENTIONS.get(project["id"])
        if geo_id is None:
            missing_projects.append(
                {**project, "join_error": f"unknown location {project['location']!r}"}
            )
            continue
        if intervention is None:
            missing_projects.append(
                {**project, "join_error": f"no intervention mapping for {project['id']}"}
            )
            continue
        key = (geo_id, project["category"], intervention)
        enriched = enriched_by_key.get(key)
        if enriched is None:
            missing_projects.append(
                {
                    **project,
                    "join_error": (
                        f"no cluster for {geo_id} / {project['category']} / {intervention}"
                    ),
                }
            )
            continue
        cluster = clusters_by_id[enriched["cluster_id"]]
        demand_parts = derive_citizen_demand(cluster, enriched)
        joined.append(
            {
                "project": project,
                "project_id": project["id"],
                "project_name": project["name"],
                "category": project["category"],
                "location": project["location"],
                "cost_cr": project["cost_cr"],
                "estimated_beneficiaries": project["estimated_beneficiaries"],
                "expected_improvement_pct": project["expected_improvement_pct"],
                "geo_id": geo_id,
                "cluster_id": enriched["cluster_id"],
                "requested_intervention": intervention,
                "seeded": {
                    "citizen_demand": project["citizen_demand"],
                    "infrastructure_deficit": project["infrastructure_deficit"],
                    "equity": project["equity"],
                    "urgency": project["urgency"],
                    "investment_gap": project["investment_gap"],
                },
                "derived": {
                    "citizen_demand_derived": demand_parts["citizen_demand_derived"],
                    "infrastructure_deficit_derived": derive_infrastructure_deficit(enriched),
                    "equity_derived": derive_equity(enriched),
                    "urgency_derived": derive_urgency(cluster["max_urgency"]),
                    "investment_gap_derived": derive_investment_gap(enriched),
                },
                "demand_components": demand_parts,
                "evidence": {
                    "unique_request_count": enriched["unique_request_count"],
                    "total_request_count": enriched["total_request_count"],
                    "requests_per_1000_residents": enriched["requests_per_1000_residents"],
                    "population": enriched["population"],
                    "max_urgency": cluster["max_urgency"],
                    "vulnerability_index": enriched["vulnerability_index"],
                    "remoteness_index": enriched["remoteness_index"],
                    "approved_or_active_investment_cr": enriched[
                        "approved_or_active_investment_cr"
                    ],
                    "urban_rural": enriched.get("urban_rural"),
                    "synthetic": True,
                },
            }
        )

    matched_cluster_ids = {row["cluster_id"] for row in joined}
    unmatched_clusters = [
        cluster for cluster in clusters if cluster["cluster_id"] not in matched_cluster_ids
    ]
    return {
        "joined": joined,
        "missing_projects": missing_projects,
        "unmatched_clusters": unmatched_clusters,
    }


def _need_inputs_from_derived(derived: dict[str, float]) -> dict[str, float]:
    return {
        "citizen_demand": derived["citizen_demand_derived"],
        "infrastructure_deficit": derived["infrastructure_deficit_derived"],
        "equity": derived["equity_derived"],
        "urgency": derived["urgency_derived"],
        "investment_gap": derived["investment_gap_derived"],
    }


def build_derived_project_record(item: dict[str, Any]) -> dict[str, Any]:
    derived = item["derived"]
    need_inputs = _need_inputs_from_derived(derived)
    need = need_score(need_contributions(need_inputs))
    impact = expected_impact(
        item["estimated_beneficiaries"],
        need,
        item["expected_improvement_pct"],
    )
    return {
        "id": item["project_id"],
        "name": item["project_name"],
        "category": item["category"],
        "location": item["location"],
        "cost_cr": item["cost_cr"],
        "estimated_beneficiaries": item["estimated_beneficiaries"],
        "expected_improvement_pct": item["expected_improvement_pct"],
        "citizen_demand_derived": derived["citizen_demand_derived"],
        "infrastructure_deficit_derived": derived["infrastructure_deficit_derived"],
        "equity_derived": derived["equity_derived"],
        "urgency_derived": derived["urgency_derived"],
        "investment_gap_derived": derived["investment_gap_derived"],
        "need_score_derived": need,
        "expected_impact_derived": impact,
        "source_cluster_id": item["cluster_id"],
        "geo_id": item["geo_id"],
        "requested_intervention": item["requested_intervention"],
        "urban_rural": item["evidence"].get("urban_rural"),
        "approved_or_active_investment_cr": item["evidence"][
            "approved_or_active_investment_cr"
        ],
        "synthetic": True,
        "input_source": "evidence_pipeline_v0.1",
        "citizen_demand_components": item["demand_components"],
        "evidence": item["evidence"],
    }


def build_derived_project_dataset(join_result: dict[str, Any]) -> dict[str, Any]:
    if join_result["missing_projects"]:
        missing = ", ".join(row["id"] for row in join_result["missing_projects"])
        raise PipelineError(f"Cannot write derived inputs; unjoined projects: {missing}")
    projects = [build_derived_project_record(item) for item in join_result["joined"]]
    projects.sort(key=lambda row: row["id"])
    return {
        "schema_version": "v0.1",
        "synthetic": True,
        "seed_projects_path": "data/seed-projects.json",
        "seed_projects_modified": False,
        "decision_inputs": "evidence_derived",
        "calibration": {
            "demand_density_tau": DEMAND_DENSITY_TAU,
            "demand_volume_cap": DEMAND_VOLUME_CAP,
            "demand_persistence_days": DEMAND_PERSISTENCE_DAYS,
            "demand_weight_density": DEMAND_WEIGHT_DENSITY,
            "demand_weight_volume": DEMAND_WEIGHT_VOLUME,
            "demand_weight_urgency": DEMAND_WEIGHT_URGENCY,
            "demand_weight_persistence": DEMAND_WEIGHT_PERSISTENCE,
            "equity_vulnerability_weight": 0.70,
            "equity_remoteness_weight": 0.30,
        },
        "need_weights": dict(NEED_WEIGHTS),
        "unmatched_clusters": [
            {
                "cluster_id": cluster["cluster_id"],
                "request_ids": cluster["request_ids"],
                "category": cluster["category"],
                "location": cluster["canonical_location"],
            }
            for cluster in join_result["unmatched_clusters"]
        ],
        "projects": projects,
    }


def write_derived_project_inputs(
    dataset: dict[str, Any],
    path: Path = DERIVED_DATA_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_derived_project_inputs(path: Path = DERIVED_DATA_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise PipelineError(f"Derived project inputs not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("projects"), list) or not raw["projects"]:
        raise PipelineError(f"{path} must contain a non-empty 'projects' array")
    return raw


def derived_projects_for_optimizer(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    """Map derived fields onto optimizer/scoring names. Does not use seeded need inputs."""
    scored: list[dict[str, Any]] = []
    for row in dataset["projects"]:
        need_inputs = _need_inputs_from_derived(row)
        parts = need_contributions(need_inputs)
        need = need_score(parts)
        impact = expected_impact(
            row["estimated_beneficiaries"],
            need,
            row["expected_improvement_pct"],
        )
        if need != row["need_score_derived"] or impact != row["expected_impact_derived"]:
            raise PipelineError(
                f"{row['id']}: stored need/impact "
                f"{row['need_score_derived']}/{row['expected_impact_derived']} "
                f"do not match recomputed {need}/{impact}"
            )
        scored.append(
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "location": row["location"],
                "cost_cr": row["cost_cr"],
                "estimated_beneficiaries": row["estimated_beneficiaries"],
                "expected_improvement_pct": row["expected_improvement_pct"],
                **need_inputs,
                "need_contributions": parts,
                "contributions": parts,
                "need_score": need,
                "expected_impact": impact,
                "priority_score": need,
                "source_cluster_id": row["source_cluster_id"],
                "synthetic": row.get("synthetic", True),
            }
        )
    scored.sort(key=lambda item: (-item["expected_impact"], item["id"]))
    return scored


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


def _comparison_rows(
    joined: list[dict[str, Any]],
    seeded_field: str,
    derived_field: str,
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for item in joined:
        seeded = float(item["seeded"][seeded_field])
        derived = float(item["derived"][derived_field])
        rows.append(
            (
                item["project_id"],
                item["project_name"],
                f"{seeded:.2f}",
                f"{derived:.2f}",
                f"{derived - seeded:+.2f}",
            )
        )
    return rows


def print_report(result: dict[str, Any]) -> None:
    joined = result["joined"]
    missing = result["missing_projects"]
    unmatched = result["unmatched_clusters"]

    print("CivicPrior — Evidence-derived project inputs (Phase 10)")
    print("seed-projects.json was not modified.")
    print()
    print(f"Candidate projects:     {len(joined) + len(missing)}")
    print(f"Successful joins:       {len(joined)}")
    print(f"Projects with no cluster: {len(missing)}")
    print(f"Clusters with no project: {len(unmatched)}")
    print()
    if missing:
        print("Unjoined projects")
        for project in missing:
            print(f"  {project['id']} {project['name']}: {project['join_error']}")
        print()
    if unmatched:
        print("Unmatched clusters (demand with no candidate project)")
        for cluster in unmatched:
            print(
                f"  {cluster['cluster_id']}: "
                f"{', '.join(cluster['request_ids'])} "
                f"({cluster['category']}, {cluster['canonical_location']})"
            )
        print()

    print("Join quality notes")
    print(
        "  Ward 9 has two demand clusters (healthcare + roads). "
        "Only healthcare joins P006; roads has no candidate project."
    )
    print(
        "  Join is 1:1 on geo_id + category + requested_intervention, "
        "not location name alone."
    )
    print()

    print("Proposed citizen_demand_derived formula")
    print(CITIZEN_DEMAND_FORMULA)
    print()
    print("Demand component breakdown")
    print(
        _format_table(
            (
                "ID",
                "Unique",
                "Req/1000",
                "Density",
                "Volume",
                "Urgency",
                "Persist",
                "Derived demand",
            ),
            [
                (
                    item["project_id"],
                    str(item["evidence"]["unique_request_count"]),
                    f"{item['evidence']['requests_per_1000_residents']:.4f}",
                    f"{item['demand_components']['density_score']:.2f}",
                    f"{item['demand_components']['volume_score']:.2f}",
                    f"{item['demand_components']['urgency_score']:.0f}",
                    f"{item['demand_components']['persistence_score']:.2f}",
                    f"{item['derived']['citizen_demand_derived']:.2f}",
                )
                for item in joined
            ],
        )
    )
    print()

    print("Safe derived fields (direct evidence mappings)")
    print("infrastructure_deficit_derived = infrastructure_deficit_score")
    print("equity_derived = 0.70*vulnerability_index + 0.30*remoteness_index")
    print("urgency_derived = low25 / medium50 / high75 / critical100")
    print("investment_gap_derived = investment_gap_score")
    print()

    print("Proposed citizen_demand comparison (not yet used by scoring)")
    print(
        _format_table(
            ("ID", "Project", "Seeded", "Derived", "Δ (derived−seeded)"),
            _comparison_rows(joined, "citizen_demand", "citizen_demand_derived"),
        )
    )
    demand_diffs = [
        abs(item["derived"]["citizen_demand_derived"] - item["seeded"]["citizen_demand"])
        for item in joined
    ]
    print(f"Mean |Δ|: {sum(demand_diffs) / len(demand_diffs) if demand_diffs else 0.0:.2f}")
    print()

    for seeded_field, derived_field in SAFE_COMPARE_FIELDS:
        print(f"Comparison: {seeded_field} vs {derived_field}")
        print(
            _format_table(
                ("ID", "Project", "Seeded", "Derived", "Δ (derived−seeded)"),
                _comparison_rows(joined, seeded_field, derived_field),
            )
        )
        diffs = [
            abs(item["derived"][derived_field] - item["seeded"][seeded_field])
            for item in joined
        ]
        mean_abs = sum(diffs) / len(diffs) if diffs else 0.0
        print(f"Mean |Δ|: {mean_abs:.2f}")
        print()


def main() -> int:
    try:
        loaded = load_enriched_pipeline()
        result = join_projects_to_evidence(
            loaded["projects"],
            loaded["clusters"],
            loaded["enriched"],
        )
        dataset = build_derived_project_dataset(result)
        write_derived_project_inputs(dataset)
    except (DataError, RequestError, ClusterError, EvidenceError, PipelineError) as exc:
        print(f"CivicPrior project-evidence pipeline failed: {exc}", file=sys.stderr)
        return 1

    print_report(result)
    print(f"Wrote {DERIVED_DATA_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
