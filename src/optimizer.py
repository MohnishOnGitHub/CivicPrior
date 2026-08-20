"""CivicPrior v0.1 budget optimizer.

Enumerates feasible project combinations and selects the portfolio
that maximizes total expected_impact without exceeding the budget.

Policy constraints are optional. With default scenario settings the search
is identical to the unconstrained baseline:

    expected_impact = estimated_beneficiaries
        * (need_score / 100)
        * (expected_improvement_pct / 100)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scoring import DATA_PATH, DataError, REPO_ROOT, SCORE_MAX, SCORE_MIN, load_projects, score_projects


DEFAULT_BUDGET_CR = 50.0
UNSELECTED_PREVIEW = 5
UNDERSERVED_EQUITY_MIN = 85
HIGH_NEED_SCORE_MIN = 85


class OptimizerError(Exception):
    """Invalid optimizer input or an infeasible internal result."""


@dataclass
class Scenario:
    """Policy settings for one optimizer run. Defaults are unconstrained."""

    budget_cr: float
    min_underserved_budget_share: float = 0.0
    min_underserved_impact_share: float = 0.0
    min_category_projects: dict[str, int] = field(default_factory=dict)
    name: str = "unconstrained"
    underserved_equity_min: float = UNDERSERVED_EQUITY_MIN

    @classmethod
    def from_dict(cls, raw: dict[str, Any], name: str = "") -> "Scenario":
        if not isinstance(raw, dict):
            raise OptimizerError("Scenario config must be a JSON object")
        if "budget_cr" not in raw:
            raise OptimizerError("Scenario config missing 'budget_cr'")
        categories_raw = raw.get("min_category_projects") or {}
        if not isinstance(categories_raw, dict):
            raise OptimizerError("'min_category_projects' must be an object of category → count")
        categories: dict[str, int] = {}
        for category, count in categories_raw.items():
            if not isinstance(category, str) or not category.strip():
                raise OptimizerError(f"Invalid category name: {category!r}")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise OptimizerError(
                    f"min_category_projects[{category!r}] must be an integer >= 0, got {count!r}"
                )
            if count > 0:
                categories[category.strip()] = count
        return cls(
            budget_cr=validate_budget(raw["budget_cr"]),
            min_underserved_budget_share=_validate_share(
                raw.get("min_underserved_budget_share", 0.0),
                "min_underserved_budget_share",
            ),
            min_underserved_impact_share=_validate_share(
                raw.get("min_underserved_impact_share", 0.0),
                "min_underserved_impact_share",
            ),
            min_category_projects=categories,
            name=name or str(raw.get("name") or "custom"),
            underserved_equity_min=_validate_equity_min(
                raw.get("underserved_equity_min", UNDERSERVED_EQUITY_MIN)
            ),
        )

    def required_underserved_spend(self) -> float:
        return round(self.budget_cr * self.min_underserved_budget_share, 2)

    def has_active_constraints(self) -> bool:
        return (
            self.min_underserved_budget_share > 0
            or self.min_underserved_impact_share > 0
            or bool(self.min_category_projects)
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select the highest-impact CivicPrior portfolio under a budget."
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=DEFAULT_BUDGET_CR,
        metavar="CR",
        help=f"Budget in crores (default: {DEFAULT_BUDGET_CR:.0f})",
    )
    parser.add_argument(
        "--min-underserved-share",
        type=float,
        default=0.0,
        metavar="SHARE",
        help="Minimum underserved spend as a share of available budget (default: 0)",
    )
    parser.add_argument(
        "--min-underserved-impact-share",
        type=float,
        default=0.0,
        metavar="SHARE",
        help="Minimum underserved expected_impact as a share of selected portfolio impact (default: 0)",
    )
    parser.add_argument(
        "--min-category",
        action="append",
        default=[],
        metavar="CATEGORY=N",
        help="Optional minimum project count by category. Repeatable. Example: healthcare=1",
    )
    parser.add_argument(
        "--scenario-json",
        type=Path,
        default=None,
        help="Load scenario config JSON (overrides --budget and constraint flags)",
    )
    return parser.parse_args(argv)


def validate_budget(budget: float) -> float:
    if isinstance(budget, bool) or not isinstance(budget, (int, float)):
        raise OptimizerError(f"Budget must be a number, got {budget!r}")
    if budget != budget:  # NaN
        raise OptimizerError("Budget cannot be NaN")
    if budget < 0:
        raise OptimizerError(f"Budget must be >= 0, got {budget}")
    return float(budget)


def _validate_share(share: Any, field_name: str = "share") -> float:
    if isinstance(share, bool) or not isinstance(share, (int, float)):
        raise OptimizerError(f"{field_name} must be a number, got {share!r}")
    value = float(share)
    if value != value:
        raise OptimizerError(f"{field_name} cannot be NaN")
    if not 0.0 <= value <= 1.0:
        raise OptimizerError(f"{field_name} must be between 0 and 1, got {value}")
    return value


def _parse_category_flag(raw: str) -> tuple[str, int]:
    category, separator, count_text = raw.partition("=")
    if not separator or not category.strip():
        raise OptimizerError(f"Expected CATEGORY=COUNT, got {raw!r}")
    try:
        count = int(count_text)
    except ValueError as exc:
        raise OptimizerError(f"Category count must be an integer: {raw!r}") from exc
    if count < 0:
        raise OptimizerError(f"Category count must be >= 0, got {count}")
    return category.strip(), count


def scenario_from_args(args: argparse.Namespace) -> Scenario:
    if args.scenario_json is not None:
        path = args.scenario_json
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise OptimizerError(f"Could not read scenario file {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OptimizerError(f"Invalid JSON in {path}: {exc}") from exc
        return Scenario.from_dict(raw, name=path.stem)

    categories: dict[str, int] = {}
    for item in args.min_category:
        category, count = _parse_category_flag(item)
        if count > 0:
            categories[category] = count
    spend_share = _validate_share(args.min_underserved_share, "min_underserved_budget_share")
    impact_share = _validate_share(
        args.min_underserved_impact_share,
        "min_underserved_impact_share",
    )
    constrained = bool(categories or spend_share or impact_share)
    return Scenario(
        budget_cr=validate_budget(args.budget),
        min_underserved_budget_share=spend_share,
        min_underserved_impact_share=impact_share,
        min_category_projects=categories,
        name="custom" if constrained else "unconstrained",
    )


def _validate_equity_min(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OptimizerError(f"underserved_equity_min must be a number, got {value!r}")
    equity_min = float(value)
    if equity_min != equity_min:
        raise OptimizerError("underserved_equity_min cannot be NaN")
    if not SCORE_MIN <= equity_min <= SCORE_MAX:
        raise OptimizerError(
            f"underserved_equity_min must be between {SCORE_MIN} and {SCORE_MAX}, "
            f"got {equity_min}"
        )
    return equity_min


def is_underserved(
    project: dict[str, Any],
    equity_min: float = UNDERSERVED_EQUITY_MIN,
) -> bool:
    return project["equity"] >= equity_min


def is_high_need(project: dict[str, Any]) -> bool:
    return project["need_score"] >= HIGH_NEED_SCORE_MIN


def underserved_spend(
    projects: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    equity_min: float = UNDERSERVED_EQUITY_MIN,
) -> float:
    return round(
        sum(project["cost_cr"] for project in projects if is_underserved(project, equity_min)),
        2,
    )


def underserved_expected_impact(
    projects: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    equity_min: float = UNDERSERVED_EQUITY_MIN,
) -> float:
    return round(
        sum(
            project["expected_impact"]
            for project in projects
            if is_underserved(project, equity_min)
        ),
        2,
    )


def impact_share(part: float, total: float) -> float | None:
    """Share of total expected_impact. None when total impact is zero."""
    if total <= 0:
        return None
    return round(part / total, 4)


def _meets_underserved_spend_constraint(
    combo: tuple[dict[str, Any], ...],
    scenario: Scenario,
) -> bool:
    return underserved_spend(combo, scenario.underserved_equity_min) >= scenario.required_underserved_spend()


def _meets_underserved_impact_constraint(
    combo: tuple[dict[str, Any], ...],
    scenario: Scenario,
) -> bool:
    required = scenario.min_underserved_impact_share
    if required <= 0:
        return True
    total = round(sum(project["expected_impact"] for project in combo), 2)
    if total <= 0:
        return False
    share = underserved_expected_impact(combo, scenario.underserved_equity_min) / total
    return share + 1e-12 >= required


def category_counts(projects: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for project in projects:
        category = project["category"]
        counts[category] = counts.get(category, 0) + 1
    return counts


def category_spend(projects: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> dict[str, float]:
    costs: dict[str, float] = {}
    for project in projects:
        category = project["category"]
        costs[category] = costs.get(category, 0.0) + project["cost_cr"]
    return {category: round(cost, 2) for category, cost in costs.items()}


def _meets_category_constraint(
    combo: tuple[dict[str, Any], ...],
    scenario: Scenario,
) -> bool:
    counts = category_counts(combo)
    for category, minimum in scenario.min_category_projects.items():
        if counts.get(category, 0) < minimum:
            return False
    return True


def _portfolio_sort_key(combo: tuple[dict[str, Any], ...]) -> tuple[Any, ...]:
    """Deterministic comparison: max impact, then min cost, then more projects, then IDs."""
    impact = round(sum(project["expected_impact"] for project in combo), 2)
    cost = round(sum(project["cost_cr"] for project in combo), 2)
    ids = tuple(sorted(project["id"] for project in combo))
    return (impact, -cost, len(combo), ids)


def _infeasible_reasons(
    scenario: Scenario,
    saw_spend: bool,
    saw_impact: bool,
    saw_category: bool,
    saw_all: bool,
) -> list[str]:
    reasons: list[str] = []
    individually_ok = True
    required_spend = scenario.required_underserved_spend()
    if scenario.min_underserved_budget_share > 0:
        individually_ok = individually_ok and saw_spend
        if not saw_spend:
            reasons.append(
                "Could not satisfy min_underserved_budget_share="
                f"{scenario.min_underserved_budget_share:.0%}: need ≥ ₹{required_spend:.2f} Cr "
                f"of selected cost on projects with equity ≥ {scenario.underserved_equity_min:.2f} "
                f"(denominator is available budget ₹{scenario.budget_cr:.0f} Cr, not selected spend)."
            )
    if scenario.min_underserved_impact_share > 0:
        individually_ok = individually_ok and saw_impact
        if not saw_impact:
            reasons.append(
                "Could not satisfy min_underserved_impact_share="
                f"{scenario.min_underserved_impact_share:.0%}: at least that share of "
                "selected expected_impact must come from projects with "
                f"equity ≥ {scenario.underserved_equity_min:.2f}."
            )
    if scenario.min_category_projects:
        individually_ok = individually_ok and saw_category
        if not saw_category:
            required_counts = ", ".join(
                f"{category}≥{count}"
                for category, count in sorted(scenario.min_category_projects.items())
            )
            reasons.append(
                f"Could not satisfy min_category_projects ({required_counts}) "
                f"under budget ₹{scenario.budget_cr:.0f} Cr."
            )
    active_count = sum(
        [
            scenario.min_underserved_budget_share > 0,
            scenario.min_underserved_impact_share > 0,
            bool(scenario.min_category_projects),
        ]
    )
    if individually_ok and not saw_all and active_count >= 2:
        reasons.append(
            "Each active constraint is feasible on its own, but no portfolio "
            "satisfies them together."
        )
    if not reasons:
        reasons.append(
            "No feasible portfolio satisfies the active scenario constraints "
            f"under budget ₹{scenario.budget_cr:.0f} Cr."
        )
    return reasons


def high_need_breakdown(
    catalog: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    high_need = [project for project in catalog if is_high_need(project)]
    selected_ids = {project["id"] for project in selected}
    selected_high_need = [project for project in high_need if project["id"] in selected_ids]
    unselected_high_need = [
        project for project in high_need if project["id"] not in selected_ids
    ]
    total = len(high_need)
    coverage = round(100.0 * len(selected_high_need) / total, 2) if total else None
    return {
        "high_need_total": total,
        "high_need_selected": selected_high_need,
        "high_need_unselected": unselected_high_need,
        "high_need_selected_ids": [project["id"] for project in selected_high_need],
        "high_need_unselected_ids": [project["id"] for project in unselected_high_need],
        "high_need_project_coverage_pct": coverage,
    }


def _metrics(
    projects: list[dict[str, Any]],
    budget: float,
    catalog: list[dict[str, Any]] | None = None,
    equity_min: float = UNDERSERVED_EQUITY_MIN,
) -> dict[str, Any]:
    total_cost = round(sum(project["cost_cr"] for project in projects), 2)
    total_impact = round(sum(project["expected_impact"] for project in projects), 2)
    underserved_cost = underserved_spend(projects, equity_min)
    underserved_impact = underserved_expected_impact(projects, equity_min)
    spend_share = round(underserved_cost / budget, 4) if budget else 0.0
    source = catalog if catalog is not None else projects
    return {
        "selected": projects,
        "count": len(projects),
        "total_cost": total_cost,
        "unused_budget": round(budget - total_cost, 2),
        "total_impact": total_impact,
        "total_need": round(sum(project["need_score"] for project in projects), 2),
        "total_priority": round(sum(project["priority_score"] for project in projects), 2),
        "underserved_spend": underserved_cost,
        "underserved_share_of_budget": spend_share,
        "underserved_expected_impact": underserved_impact,
        "underserved_impact_share": impact_share(underserved_impact, total_impact),
        "underserved_ids": [
            project["id"] for project in projects if is_underserved(project, equity_min)
        ],
        "underserved_equity_min": equity_min,
        "category_counts": category_counts(projects),
        "category_spend": category_spend(projects),
        "category_mix": format_category_mix(projects),
        **high_need_breakdown(source, projects),
    }


def select_portfolio(
    projects: list[dict[str, Any]],
    budget: float | Scenario,
) -> dict[str, Any]:
    scenario = (
        budget
        if isinstance(budget, Scenario)
        else Scenario(budget_cr=validate_budget(budget), name="unconstrained")
    )
    scenario.budget_cr = validate_budget(scenario.budget_cr)
    scenario.min_underserved_budget_share = _validate_share(
        scenario.min_underserved_budget_share,
        "min_underserved_budget_share",
    )
    scenario.min_underserved_impact_share = _validate_share(
        scenario.min_underserved_impact_share,
        "min_underserved_impact_share",
    )
    scenario.underserved_equity_min = _validate_equity_min(scenario.underserved_equity_min)

    if not projects:
        raise OptimizerError("No scored projects available to optimize")

    best: tuple[dict[str, Any], ...] | None = None
    best_key: tuple[Any, ...] | None = None
    saw_spend = False
    saw_impact = False
    saw_category = False
    saw_all = False

    for size in range(len(projects) + 1):
        for combo in combinations(projects, size):
            cost = sum(project["cost_cr"] for project in combo)
            if cost > scenario.budget_cr:
                continue
            spend_ok = _meets_underserved_spend_constraint(combo, scenario)
            impact_ok = _meets_underserved_impact_constraint(combo, scenario)
            category_ok = _meets_category_constraint(combo, scenario)
            saw_spend = saw_spend or spend_ok
            saw_impact = saw_impact or impact_ok
            saw_category = saw_category or category_ok
            if not (spend_ok and impact_ok and category_ok):
                continue
            saw_all = True
            key = _portfolio_sort_key(combo)
            if best_key is None or key > best_key:
                best = combo
                best_key = key

    ranked = sorted(
        projects,
        key=lambda project: (-project["expected_impact"], project["id"]),
    )
    base = {
        "feasible": False,
        "scenario": scenario,
        "budget": scenario.budget_cr,
        "all_projects": ranked,
        "unselected": ranked,
        "infeasible_reasons": [],
    }

    if best is None:
        return {
            **base,
            **_metrics(
                [],
                scenario.budget_cr,
                catalog=ranked,
                equity_min=scenario.underserved_equity_min,
            ),
            "infeasible_reasons": _infeasible_reasons(
                scenario,
                saw_spend,
                saw_impact,
                saw_category,
                saw_all,
            ),
        }

    selected = sorted(
        best,
        key=lambda project: (-project["expected_impact"], project["id"]),
    )
    selected_ids = {project["id"] for project in selected}
    unselected = [project for project in ranked if project["id"] not in selected_ids]
    result = {
        **base,
        **_metrics(
            selected,
            scenario.budget_cr,
            catalog=ranked,
            equity_min=scenario.underserved_equity_min,
        ),
        "feasible": True,
        "unselected": unselected,
    }
    if result["total_cost"] > scenario.budget_cr:
        raise OptimizerError(
            f"Internal error: selected cost ₹{result['total_cost']} Cr "
            f"exceeds budget ₹{scenario.budget_cr} Cr"
        )
    required_spend = scenario.required_underserved_spend()
    if result["underserved_spend"] + 1e-9 < required_spend:
        raise OptimizerError(
            f"Internal error: underserved spend ₹{result['underserved_spend']} Cr "
            f"is below required ₹{required_spend} Cr"
        )
    required_impact_share = scenario.min_underserved_impact_share
    if required_impact_share > 0:
        share = result["underserved_impact_share"]
        if share is None or share + 1e-12 < required_impact_share:
            raise OptimizerError(
                "Internal error: underserved impact share "
                f"{'undefined' if share is None else f'{share:.1%}'} "
                f"is below required {required_impact_share:.0%}"
            )
    return result


def binding_constraints(result: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    """Identify which active constraints the unconstrained baseline fails."""
    scenario: Scenario = result["scenario"]
    if not result.get("feasible"):
        return list(result.get("infeasible_reasons") or ["infeasible"])
    if not scenario.has_active_constraints():
        return ["none (unconstrained)"]

    baseline_selected = tuple(baseline["selected"])
    baseline_ids = {project["id"] for project in baseline["selected"]}
    result_ids = {project["id"] for project in result["selected"]}
    if result_ids == baseline_ids:
        return [
            "none — unconstrained portfolio already satisfies all active constraints"
        ]

    binds: list[str] = []
    if scenario.min_underserved_budget_share > 0 and not _meets_underserved_spend_constraint(
        baseline_selected, scenario
    ):
        binds.append(
            f"min_underserved_budget_share={scenario.min_underserved_budget_share:.0%}"
        )
    if scenario.min_underserved_impact_share > 0 and not _meets_underserved_impact_constraint(
        baseline_selected, scenario
    ):
        binds.append(
            f"min_underserved_impact_share={scenario.min_underserved_impact_share:.0%}"
        )
    if scenario.min_category_projects and not _meets_category_constraint(
        baseline_selected, scenario
    ):
        binds.append(
            "min_category_projects="
            + json.dumps(scenario.min_category_projects, sort_keys=True)
        )
    if not binds:
        binds.append("portfolio changed without a failed baseline constraint")
    return binds


def compare_to_baseline(result: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    if not baseline.get("feasible"):
        raise OptimizerError("Baseline scenario must be feasible for comparison")

    baseline_ids = {project["id"] for project in baseline["selected"]}
    if not result.get("feasible"):
        return {
            "added": [],
            "removed": sorted(baseline_ids),
            "added_projects": [],
            "removed_projects": list(baseline["selected"]),
            "impact_delta": None,
            "impact_sacrificed_pct": None,
        }

    result_ids = {project["id"] for project in result["selected"]}
    added_ids = result_ids - baseline_ids
    removed_ids = baseline_ids - result_ids
    added = [project for project in result["selected"] if project["id"] in added_ids]
    removed = [project for project in baseline["selected"] if project["id"] in removed_ids]
    impact_delta = round(result["total_impact"] - baseline["total_impact"], 2)
    baseline_impact = baseline["total_impact"]
    if baseline_impact and impact_delta < 0:
        sacrificed = round((-impact_delta / baseline_impact) * 100.0, 2)
    elif baseline_impact:
        sacrificed = 0.0
    else:
        sacrificed = None
    return {
        "added": sorted(added_ids),
        "removed": sorted(removed_ids),
        "added_projects": added,
        "removed_projects": removed,
        "impact_delta": impact_delta,
        "impact_sacrificed_pct": sacrificed,
    }


def format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
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


def format_category_mix(projects: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    if not projects:
        return "(none)"
    counts = category_counts(projects)
    costs = category_spend(projects)
    return "; ".join(
        f"{category}: {counts[category]} projects, ₹{costs[category]:.0f} Cr"
        for category in sorted(counts)
    )


def format_project_table(
    projects: list[dict[str, Any]],
    *,
    equity_min: float = UNDERSERVED_EQUITY_MIN,
) -> str:
    if not projects:
        return "(none)"
    rows = [
        (
            str(index),
            project["id"],
            project["name"],
            f"{project['need_score']:.2f}",
            f"{project['expected_impact']:.2f}",
            f"{project['equity']:.0f}",
            "yes" if is_underserved(project, equity_min) else "no",
            "yes" if is_high_need(project) else "no",
            project["category"],
            f"₹{project['cost_cr']:.0f} Cr",
        )
        for index, project in enumerate(projects, start=1)
    ]
    return format_table(
        (
            "#",
            "ID",
            "Project",
            "Need",
            "Impact",
            "Equity",
            "Underserved",
            "High-need",
            "Category",
            "Cost",
        ),
        rows,
    )


def print_report(result: dict[str, Any], *, show_catalog: bool = True) -> None:
    scenario: Scenario = result["scenario"]
    print("CivicPrior — Budget Optimizer (v0.1)")
    print(f"Source: {DATA_PATH.relative_to(REPO_ROOT)}")
    print(f"Scenario: {scenario.name}")
    print("Objective: maximize sum of expected_impact")
    print(
        "expected_impact = estimated_beneficiaries × (need_score/100) "
        "× (expected_improvement_pct/100)"
    )
    print(f"Underserved rule: equity ≥ {scenario.underserved_equity_min:.2f}")
    print(f"High-need rule: need_score ≥ {HIGH_NEED_SCORE_MIN} (reporting only)")
    print(f"min_underserved_budget_share: {scenario.min_underserved_budget_share:.0%}")
    print(f"min_underserved_impact_share: {scenario.min_underserved_impact_share:.0%}")
    print(
        "min_category_projects: "
        + (
            json.dumps(scenario.min_category_projects, sort_keys=True)
            if scenario.min_category_projects
            else "{}"
        )
    )
    print("Search: exhaustive enumeration of feasible subsets")
    print()
    if show_catalog:
        print("All projects by expected_impact")
        print(format_project_table(result["all_projects"], equity_min=scenario.underserved_equity_min))
        print()

    print(f"Budget:                      ₹{result['budget']:.0f} Cr")
    if not result["feasible"]:
        print("Status:                      INFEASIBLE")
        print("Constraints were not relaxed.")
        for reason in result["infeasible_reasons"]:
            print(f"  - {reason}")
        return

    print("Status:                      feasible")
    print(f"Selected projects:           {result['count']}")
    print(f"Total cost:                  ₹{result['total_cost']:.0f} Cr")
    print(f"Unused budget:               ₹{result['unused_budget']:.0f} Cr")
    print(f"Total expected impact:       {result['total_impact']:.2f}")
    print(f"Total need_score (ref):      {result['total_need']:.2f}")
    print(f"Total priority_score (ref):  {result['total_priority']:.2f}")
    print(f"Underserved spend:           ₹{result['underserved_spend']:.0f} Cr")
    print(
        f"Underserved share of budget: {result['underserved_share_of_budget']:.1%}"
    )
    print(f"Underserved expected impact: {result['underserved_expected_impact']:.2f}")
    impact_share_text = (
        "n/a (total expected impact is 0)"
        if result["underserved_impact_share"] is None
        else f"{result['underserved_impact_share']:.1%}"
    )
    print(f"Underserved impact share:    {impact_share_text}")
    coverage = result["high_need_project_coverage_pct"]
    coverage_text = "n/a (no high-need projects in catalog)" if coverage is None else f"{coverage:.2f}%"
    print(
        f"High-need projects:          {result['high_need_total']} in catalog; "
        f"{len(result['high_need_selected_ids'])} selected; "
        f"{len(result['high_need_unselected_ids'])} unselected; "
        f"coverage {coverage_text}"
    )
    print(
        "High-need selected:          "
        + (", ".join(result["high_need_selected_ids"]) or "(none)")
    )
    print(
        "High-need unselected:        "
        + (", ".join(result["high_need_unselected_ids"]) or "(none)")
    )
    print(f"Category mix:                {result['category_mix']}")
    print()
    print("Selected portfolio")
    print(format_project_table(result["selected"], equity_min=scenario.underserved_equity_min))
    print()
    print(f"Highest-impact unselected projects (top {UNSELECTED_PREVIEW})")
    print(format_project_table(result["unselected"][:UNSELECTED_PREVIEW], equity_min=scenario.underserved_equity_min))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        scenario = scenario_from_args(args)
        projects = score_projects(load_projects(DATA_PATH))
        result = select_portfolio(projects, scenario)
    except (DataError, OptimizerError) as exc:
        print(f"CivicPrior optimizer failed: {exc}", file=sys.stderr)
        return 1

    print_report(result)
    return 0 if result["feasible"] else 1


if __name__ == "__main__":
    sys.exit(main())
