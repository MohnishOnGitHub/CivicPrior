"""CivicPrior v0.1 scenario comparison.

Runs named policy scenarios against the same scored project set and
compares each constrained result to the unconstrained baseline.

Default constraints are off. Fairness/category rules are scenario inputs,
not CivicPrior defaults.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from optimizer import (
    HIGH_NEED_SCORE_MIN,
    UNDERSERVED_EQUITY_MIN,
    OptimizerError,
    Scenario,
    binding_constraints,
    compare_to_baseline,
    format_project_table,
    format_table,
    print_report,
    select_portfolio,
    validate_budget,
)
from scoring import DATA_PATH, DataError, REPO_ROOT, load_projects, score_projects


DEFAULT_COMPARE_BUDGET_CR = 60.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare CivicPrior policy scenarios against an unconstrained baseline."
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=DEFAULT_COMPARE_BUDGET_CR,
        metavar="CR",
        help=f"Budget in crores for every named scenario (default: {DEFAULT_COMPARE_BUDGET_CR:.0f})",
    )
    return parser.parse_args(argv)


def named_scenarios(budget_cr: float) -> list[Scenario]:
    return [
        Scenario(
            name="A. BASELINE",
            budget_cr=budget_cr,
        ),
        Scenario(
            name="B. IMPACT EQUITY 25%",
            budget_cr=budget_cr,
            min_underserved_impact_share=0.25,
        ),
        Scenario(
            name="C. IMPACT EQUITY 30%",
            budget_cr=budget_cr,
            min_underserved_impact_share=0.30,
        ),
        Scenario(
            name="D. IMPACT EQUITY 40%",
            budget_cr=budget_cr,
            min_underserved_impact_share=0.40,
        ),
        Scenario(
            name="E. IMPACT EQUITY 30% + HEALTHCARE",
            budget_cr=budget_cr,
            min_underserved_impact_share=0.30,
            min_category_projects={"healthcare": 1},
        ),
    ]


def _ids(projects: list[dict]) -> str:
    if not projects:
        return "(none)"
    return ", ".join(project["id"] for project in projects)


def print_comparison(results: list[dict], baseline: dict) -> None:
    budget = baseline["budget"]
    print("CivicPrior — Scenario Comparison")
    print(f"Source: {DATA_PATH.relative_to(REPO_ROOT)}")
    print(f"Budget: ₹{budget:.0f} Cr for every scenario")
    print(f"Underserved rule: equity ≥ {UNDERSERVED_EQUITY_MIN}")
    print(f"High-need rule: need_score ≥ {HIGH_NEED_SCORE_MIN} (reporting only, not a constraint)")
    print("Underserved spend share denominator: available budget")
    print("Underserved impact share denominator: selected portfolio expected_impact")
    print("Objective: maximize expected_impact among subsets that meet active constraints")
    print("Infeasible scenarios are not relaxed.")
    print()

    summary_rows: list[tuple[str, ...]] = []
    for result in results:
        scenario: Scenario = result["scenario"]
        diff = compare_to_baseline(result, baseline)
        if result["feasible"]:
            sacrificed = diff["impact_sacrificed_pct"]
            sacrificed_text = f"{sacrificed:.2f}%" if sacrificed is not None else "n/a"
            impact_share_text = (
                "n/a"
                if result["underserved_impact_share"] is None
                else f"{result['underserved_impact_share']:.1%}"
            )
            coverage = result["high_need_project_coverage_pct"]
            coverage_text = "n/a" if coverage is None else f"{coverage:.1f}%"
            summary_rows.append(
                (
                    scenario.name,
                    "yes",
                    f"₹{result['total_cost']:.0f}",
                    f"₹{result['unused_budget']:.0f}",
                    f"{result['total_impact']:.2f}",
                    f"{diff['impact_delta']:+.2f}",
                    sacrificed_text,
                    f"₹{result['underserved_spend']:.0f}",
                    f"{result['underserved_share_of_budget']:.1%}",
                    f"{result['underserved_expected_impact']:.2f}",
                    impact_share_text,
                    coverage_text,
                    result["category_mix"],
                    ", ".join(diff["added"]) or "(none)",
                    ", ".join(diff["removed"]) or "(none)",
                    "; ".join(binding_constraints(result, baseline)),
                )
            )
        else:
            summary_rows.append(
                (
                    scenario.name,
                    "NO",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "infeasible",
                    "—",
                    ", ".join(diff["removed"]) or "—",
                    "; ".join(binding_constraints(result, baseline)),
                )
            )

    print("Summary versus unconstrained baseline")
    print(
        format_table(
            (
                "Scenario",
                "Feasible",
                "Cost",
                "Unused",
                "Impact",
                "Δ impact",
                "Impact sacrificed",
                "Underserved spend",
                "Spend share",
                "Underserved impact",
                "Impact share",
                "High-need coverage",
                "Category mix",
                "Added",
                "Removed",
                "Binds",
            ),
            summary_rows,
        )
    )
    print()

    for result in results:
        scenario: Scenario = result["scenario"]
        diff = compare_to_baseline(result, baseline)
        print("=" * 72)
        print(scenario.name)
        print(
            "config: "
            + json.dumps(
                {
                    "budget_cr": scenario.budget_cr,
                    "min_underserved_budget_share": scenario.min_underserved_budget_share,
                    "min_underserved_impact_share": scenario.min_underserved_impact_share,
                    "min_category_projects": scenario.min_category_projects,
                },
                sort_keys=True,
            )
        )
        print()
        print_report(result, show_catalog=False)
        print()
        print("Versus baseline")
        print("  binds:    " + "; ".join(binding_constraints(result, baseline)))
        if not result["feasible"]:
            print("  added:    n/a (infeasible)")
            print(f"  removed:  {_ids(diff['removed_projects'])}")
            print("  Δ impact: n/a")
            print("  impact sacrificed: n/a")
        else:
            print(f"  added:    {_ids(diff['added_projects'])}")
            print(f"  removed:  {_ids(diff['removed_projects'])}")
            print(f"  Δ impact: {diff['impact_delta']:+.2f}")
            sacrificed = diff["impact_sacrificed_pct"]
            print(
                "  impact sacrificed: "
                + (f"{sacrificed:.2f}%" if sacrificed is not None else "n/a")
            )
            if diff["added_projects"]:
                print("  entered:")
                print(format_project_table(diff["added_projects"]))
            if diff["removed_projects"]:
                print("  left:")
                print(format_project_table(diff["removed_projects"]))
        print()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        budget = validate_budget(args.budget)
        projects = score_projects(load_projects(DATA_PATH))
        scenarios = named_scenarios(budget)
        results = [select_portfolio(projects, scenario) for scenario in scenarios]
    except (DataError, OptimizerError) as exc:
        print(f"CivicPrior scenario comparison failed: {exc}", file=sys.stderr)
        return 1

    baseline = results[0]
    if not baseline["feasible"]:
        print("CivicPrior scenario comparison failed: unconstrained baseline is infeasible", file=sys.stderr)
        return 1

    print_comparison(results, baseline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
