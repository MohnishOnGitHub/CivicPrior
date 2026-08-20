"""Compare original seeded decision inputs with evidence-derived inputs.

Does not modify seed-projects.json, scoring.py, optimizer.py, or scenarios.py.
Uses the existing deterministic optimizer on two scored catalogs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent
SRC_DIR = PIPELINE_DIR.parent
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from optimizer import (
    UNDERSERVED_EQUITY_MIN,
    OptimizerError,
    Scenario,
    compare_to_baseline,
    format_table,
    select_portfolio,
)
from project_evidence import (
    DEFAULT_DERIVED_UNDERSERVED_PERCENTILE,
    SENSITIVITY_PERCENTILES,
    PipelineError,
    build_derived_project_dataset,
    classify_underserved_by_percentile,
    derived_projects_for_optimizer,
    join_projects_to_evidence,
    load_enriched_pipeline,
    write_derived_project_inputs,
)
from scoring import DATA_PATH, DataError, load_projects, score_projects


PORTFOLIO_BUDGETS = (50.0, 60.0, 100.0)
EQUITY_BUDGET_CR = 60.0
DERIVED_SHARE_SCENARIOS: tuple[tuple[str, float], ...] = (
    ("A. BASELINE", 0.0),
    ("B. IMPACT EQUITY 25%", 0.25),
    ("C. IMPACT EQUITY 30%", 0.30),
    ("D. IMPACT EQUITY 40%", 0.40),
)
RURAL_MARKERS = ("Rural", "Village", "Periphery")


def _rank(projects: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    ranked = sorted(projects, key=lambda item: (-item[field], item["id"]))
    return [
        {
            "rank": index,
            "id": project["id"],
            "name": project["name"],
            "value": project[field],
            "location": project["location"],
            "cost_cr": project["cost_cr"],
            "equity": project["equity"],
        }
        for index, project in enumerate(ranked, start=1)
    ]


def _rank_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in rows}


def _ids(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return "(none)"
    return ", ".join(project["id"] for project in projects)


def _is_rural(project: dict[str, Any], derived_by_id: dict[str, dict[str, Any]]) -> bool:
    derived = derived_by_id.get(project["id"], {})
    urban_rural = derived.get("urban_rural")
    if urban_rural:
        return urban_rural == "rural"
    return any(marker in project["location"] for marker in RURAL_MARKERS)


def _has_active_investment(
    project: dict[str, Any],
    derived_by_id: dict[str, dict[str, Any]],
) -> bool:
    derived = derived_by_id.get(project["id"], {})
    return float(derived.get("approved_or_active_investment_cr") or 0) > 0


def _portfolio(projects: list[dict[str, Any]], budget: float, **constraints: Any) -> dict[str, Any]:
    scenario = Scenario(budget_cr=budget, name=constraints.pop("name", "unconstrained"), **constraints)
    return select_portfolio(projects, scenario)


def _print_classification(label: str, classification: dict[str, Any]) -> None:
    print(label)
    print(
        f"Method: {classification['method']}  "
        f"percentile={classification['percentile']:.0%}  "
        f"n={classification['catalog_size']}"
    )
    print(
        format_table(
            ("ID", "Project", "Equity derived", "Underserved"),
            [
                (
                    row["id"],
                    row["name"],
                    f"{row['equity']:.2f}",
                    "yes" if row["underserved"] else "no",
                )
                for row in classification["sorted_equities"]
            ],
        )
    )
    print(f"Calculated threshold: {classification['threshold']:.2f}")
    print(
        "Underserved projects: "
        + (", ".join(classification["underserved_ids"]) or "(none)")
    )
    print()


def _print_derived_scenarios(
    derived: list[dict[str, Any]],
    equity_min: float,
) -> None:
    results = []
    for name, share in DERIVED_SHARE_SCENARIOS:
        results.append(
            _portfolio(
                derived,
                EQUITY_BUDGET_CR,
                min_underserved_impact_share=share,
                underserved_equity_min=equity_min,
                name=name,
            )
        )
    baseline = results[0]
    print(f"Derived ₹{EQUITY_BUDGET_CR:.0f} Cr scenarios")
    print(
        f"Underserved rule: equity_derived >= {DEFAULT_DERIVED_UNDERSERVED_PERCENTILE:.0%} "
        f"percentile of this catalog (= {equity_min:.2f})"
    )
    print("Seeded equity >= 85 rule is not used here.")
    print()
    summary_rows: list[tuple[str, ...]] = []
    for result in results:
        diff = compare_to_baseline(result, baseline)
        share = result.get("underserved_impact_share")
        share_text = "n/a" if share is None else f"{share:.1%}"
        if result["feasible"]:
            sacrificed = diff["impact_sacrificed_pct"]
            sacrificed_text = f"{sacrificed:.2f}%" if sacrificed is not None else "n/a"
            summary_rows.append(
                (
                    result["scenario"].name,
                    "yes",
                    ", ".join(p["id"] for p in result["selected"]) or "(none)",
                    f"₹{result['total_cost']:.0f} Cr",
                    f"₹{result['unused_budget']:.0f} Cr",
                    f"{result['total_impact']:.2f}",
                    share_text,
                    f"{diff['impact_delta']:+.2f}" if diff["impact_delta"] is not None else "n/a",
                    sacrificed_text,
                    ", ".join(diff["added"]) or "(none)",
                    ", ".join(diff["removed"]) or "(none)",
                )
            )
        else:
            summary_rows.append(
                (
                    result["scenario"].name,
                    "NO",
                    "(infeasible)",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    ", ".join(diff["removed"]) or "—",
                )
            )
    print(
        format_table(
            (
                "Scenario",
                "Feasible",
                "Selected",
                "Cost",
                "Unused",
                "Impact",
                "Underserved impact share",
                "Δ impact vs A",
                "Impact sacrificed",
                "Added",
                "Removed",
            ),
            summary_rows,
        )
    )
    print()
    for result in results:
        diff = compare_to_baseline(result, baseline)
        print(result["scenario"].name)
        if not result["feasible"]:
            print("  Status: INFEASIBLE")
            for reason in result.get("infeasible_reasons") or []:
                print(f"    - {reason}")
            print()
            continue
        print(f"  Selected:                 {_ids(result['selected'])}")
        print(f"  Total expected impact:    {result['total_impact']:.2f}")
        share = result["underserved_impact_share"]
        print(
            "  Underserved impact share: "
            + ("n/a" if share is None else f"{share:.1%}")
        )
        print(f"  Unused budget:            ₹{result['unused_budget']:.0f} Cr")
        print(f"  Added vs baseline:        {_ids(diff['added_projects'])}")
        print(f"  Removed vs baseline:      {_ids(diff['removed_projects'])}")
        if diff["impact_delta"] is None:
            print("  Δ impact vs baseline:     n/a")
            print("  Impact sacrificed:        n/a")
        else:
            sacrificed = diff["impact_sacrificed_pct"]
            print(f"  Δ impact vs baseline:     {diff['impact_delta']:+.2f}")
            print(
                "  Impact sacrificed:        "
                + (f"{sacrificed:.2f}%" if sacrificed is not None else "n/a")
            )
        print()


def _rank_move_rows(
    seeded_ranks: list[dict[str, Any]],
    derived_ranks: list[dict[str, Any]],
) -> list[tuple[str, ...]]:
    seeded = _rank_map(seeded_ranks)
    derived = _rank_map(derived_ranks)
    rows: list[tuple[str, ...]] = []
    for project_id in sorted(seeded):
        seed_row = seeded[project_id]
        derived_row = derived[project_id]
        delta = seed_row["rank"] - derived_row["rank"]
        rows.append(
            (
                project_id,
                seed_row["name"],
                str(seed_row["rank"]),
                f"{seed_row['value']:.2f}",
                str(derived_row["rank"]),
                f"{derived_row['value']:.2f}",
                f"{delta:+d}",
            )
        )
    rows.sort(key=lambda row: (-abs(int(row[6])), row[0]))
    return rows


def _print_portfolio_pair(
    title: str,
    seeded_result: dict[str, Any],
    derived_result: dict[str, Any],
    derived_by_id: dict[str, dict[str, Any]],
) -> None:
    seeded_ids = {project["id"] for project in seeded_result["selected"]}
    derived_ids = {project["id"] for project in derived_result["selected"]}
    entered = [project for project in derived_result["selected"] if project["id"] not in seeded_ids]
    left = [project for project in seeded_result["selected"] if project["id"] not in derived_ids]
    impact_delta = round(derived_result["total_impact"] - seeded_result["total_impact"], 2)

    print(title)
    print(
        format_table(
            ("Model", "Feasible", "IDs", "Cost", "Unused", "Impact", "Underserved impact share"),
            [
                _portfolio_summary_row("seeded", seeded_result),
                _portfolio_summary_row("derived", derived_result),
            ],
        )
    )
    print(f"Entered derived portfolio:  {_ids(entered)}")
    print(f"Left derived portfolio:     {_ids(left)}")
    print(f"Δ total expected impact:    {impact_delta:+.2f}")
    if entered:
        print("  entered:")
        for project in entered:
            print(f"    {project['id']} {project['name']}  impact={project['expected_impact']:.2f}")
    if left:
        print("  left:")
        for project in left:
            print(f"    {project['id']} {project['name']}  impact={project['expected_impact']:.2f}")

    rural_seeded = [p for p in seeded_result["selected"] if _is_rural(p, derived_by_id)]
    rural_derived = [p for p in derived_result["selected"] if _is_rural(p, derived_by_id)]
    funded_seeded = [p for p in seeded_result["selected"] if _has_active_investment(p, derived_by_id)]
    funded_derived = [p for p in derived_result["selected"] if _has_active_investment(p, derived_by_id)]
    print(f"Rural/small-cluster selected (seeded):  {_ids(rural_seeded)}")
    print(f"Rural/small-cluster selected (derived): {_ids(rural_derived)}")
    print(f"Already-funded selected (seeded):       {_ids(funded_seeded)}")
    print(f"Already-funded selected (derived):      {_ids(funded_derived)}")
    print()


def _portfolio_summary_row(label: str, result: dict[str, Any]) -> tuple[str, ...]:
    share = result.get("underserved_impact_share")
    share_text = "n/a" if share is None else f"{share:.1%}"
    if not result.get("feasible"):
        return (label, "NO", "(infeasible)", "—", "—", "—", "—")
    return (
        label,
        "yes",
        ", ".join(project["id"] for project in result["selected"]) or "(none)",
        f"₹{result['total_cost']:.0f} Cr",
        f"₹{result['unused_budget']:.0f} Cr",
        f"{result['total_impact']:.2f}",
        share_text,
    )


def print_report(
    seeded: list[dict[str, Any]],
    derived: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> None:
    derived_by_id = {row["id"]: row for row in dataset["projects"]}
    seeded_need = _rank(seeded, "need_score")
    derived_need = _rank(derived, "need_score")
    seeded_impact = _rank(seeded, "expected_impact")
    derived_impact = _rank(derived, "expected_impact")
    default_class = classify_underserved_by_percentile(
        derived,
        DEFAULT_DERIVED_UNDERSERVED_PERCENTILE,
    )
    derived_equity_min = default_class["threshold"]

    print("CivicPrior — Seeded vs evidence-derived decision models")
    print("seed-projects.json was not modified.")
    print("Derived catalog: data/derived-project-inputs.json")
    print(f"Seeded underserved rule (historical): equity ≥ {UNDERSERVED_EQUITY_MIN:.2f}")
    print(
        "Derived underserved rule: "
        f"equity_derived >= {DEFAULT_DERIVED_UNDERSERVED_PERCENTILE:.0%} percentile "
        f"of the 12-project catalog (= {derived_equity_min:.2f})"
    )
    print()

    _print_classification(
        "Derived equity distribution (ascending) and 75th-percentile underserved class",
        default_class,
    )

    print("Classification sensitivity (not used to pick a winner)")
    print(
        format_table(
            ("Percentile", "Threshold", "Count", "Underserved IDs"),
            [
                (
                    f"{pct:.0%}",
                    f"{item['threshold']:.2f}",
                    str(len(item["underserved_ids"])),
                    ", ".join(item["underserved_ids"]) or "(none)",
                )
                for pct in SENSITIVITY_PERCENTILES
                for item in [
                    classify_underserved_by_percentile(derived, pct)
                ]
            ],
        )
    )
    print()

    print("Need-score ranking")
    print(
        format_table(
            ("ID", "Project", "Seeded rank", "Seeded need", "Derived rank", "Derived need", "Δ rank"),
            _rank_move_rows(seeded_need, derived_need),
        )
    )
    print()
    print("Expected-impact ranking")
    print(
        format_table(
            ("ID", "Project", "Seeded rank", "Seeded impact", "Derived rank", "Derived impact", "Δ rank"),
            _rank_move_rows(seeded_impact, derived_impact),
        )
    )
    print()

    print("Largest need-score rank moves")
    for row in _rank_move_rows(seeded_need, derived_need)[:5]:
        direction = "up" if int(row[6]) > 0 else "down" if int(row[6]) < 0 else "unchanged"
        print(f"  {row[0]} {row[1]}: {row[2]} → {row[4]} ({row[6]}, {direction})")
    print()
    print("Largest expected-impact rank moves")
    for row in _rank_move_rows(seeded_impact, derived_impact)[:5]:
        direction = "up" if int(row[6]) > 0 else "down" if int(row[6]) < 0 else "unchanged"
        print(f"  {row[0]} {row[1]}: {row[2]} → {row[4]} ({row[6]}, {direction})")
    print()

    for budget in PORTFOLIO_BUDGETS:
        seeded_result = _portfolio(seeded, budget, name=f"seeded ₹{budget:.0f} Cr")
        derived_result = _portfolio(
            derived,
            budget,
            underserved_equity_min=derived_equity_min,
            name=f"derived ₹{budget:.0f} Cr",
        )
        _print_portfolio_pair(
            f"Unconstrained portfolio ₹{budget:.0f} Cr",
            seeded_result,
            derived_result,
            derived_by_id,
        )

    _print_derived_scenarios(derived, derived_equity_min)

    unmatched = dataset.get("unmatched_clusters") or []
    if unmatched:
        print("Demand clusters still without a candidate project")
        for cluster in unmatched:
            print(
                f"  {cluster['cluster_id']}: {', '.join(cluster['request_ids'])} "
                f"({cluster['category']}, {cluster['location']})"
            )
        print()


def main() -> int:
    try:
        loaded = load_enriched_pipeline()
        join_result = join_projects_to_evidence(
            loaded["projects"],
            loaded["clusters"],
            loaded["enriched"],
        )
        dataset = build_derived_project_dataset(join_result)
        write_derived_project_inputs(dataset)
        seeded = score_projects(load_projects(DATA_PATH))
        derived = derived_projects_for_optimizer(dataset)
    except (DataError, OptimizerError, PipelineError) as exc:
        print(f"CivicPrior decision-model comparison failed: {exc}", file=sys.stderr)
        return 1

    print_report(seeded, derived, dataset)
    print("Wrote data/derived-project-inputs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
