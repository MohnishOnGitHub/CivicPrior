"""CivicPrior Phase 0 scoring prototype.

Loads synthetic candidate projects and produces deterministic,
auditable scores.

priority_score is the original 0–100 composite, kept for comparison.
need_score is the v0.1 need composite and excludes population_affected.
expected_impact is the optimizer metric:

    expected_impact = estimated_beneficiaries
        * (need_score / 100)
        * (expected_improvement_pct / 100)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


WEIGHTS: dict[str, float] = {
    "citizen_demand": 0.30,
    "infrastructure_deficit": 0.20,
    "population_affected": 0.20,
    "equity": 0.15,
    "urgency": 0.10,
    "investment_gap": 0.05,
}

NEED_WEIGHTS: dict[str, float] = {
    "citizen_demand": 0.30,
    "infrastructure_deficit": 0.25,
    "equity": 0.20,
    "urgency": 0.15,
    "investment_gap": 0.10,
}

IDENTITY_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "category",
    "location",
    "cost_cr",
)

IMPACT_FIELDS: tuple[str, ...] = (
    "estimated_beneficiaries",
    "expected_improvement_pct",
)

SCORE_FIELDS: tuple[str, ...] = tuple(WEIGHTS.keys())
NEED_FIELDS: tuple[str, ...] = tuple(NEED_WEIGHTS.keys())
REQUIRED_FIELDS: tuple[str, ...] = IDENTITY_FIELDS + SCORE_FIELDS + IMPACT_FIELDS
SCORE_MIN = 0
SCORE_MAX = 100

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "seed-projects.json"


class DataError(Exception):
    """Malformed project data that should stop scoring."""


def _project_label(project: Any, index: int) -> str:
    if isinstance(project, dict):
        project_id = project.get("id")
        name = project.get("name")
        if project_id and name:
            return f"project {index} ({project_id}: {name})"
        if project_id:
            return f"project {index} ({project_id})"
    return f"project {index}"


def _require_number(value: Any, field: str, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataError(f"{label}: '{field}' must be a number, got {value!r}")
    return float(value)


def _require_positive_int(value: Any, field: str, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(f"{label}: '{field}' must be an integer, got {value!r}")
    if value <= 0:
        raise DataError(f"{label}: '{field}' must be > 0, got {value}")
    return value


def validate_project(project: Any, index: int) -> dict[str, Any]:
    label = _project_label(project, index)

    if not isinstance(project, dict):
        raise DataError(f"{label}: expected an object, got {type(project).__name__}")

    missing = [field for field in REQUIRED_FIELDS if field not in project]
    if missing:
        raise DataError(f"{label}: missing required field(s): {', '.join(missing)}")

    for field in ("id", "name", "category", "location"):
        value = project[field]
        if not isinstance(value, str) or not value.strip():
            raise DataError(f"{label}: '{field}' must be a non-empty string")

    cost = _require_number(project["cost_cr"], "cost_cr", label)
    if cost < 0:
        raise DataError(f"{label}: 'cost_cr' must be >= 0, got {cost}")

    scores: dict[str, float] = {}
    for field in SCORE_FIELDS:
        score = _require_number(project[field], field, label)
        if not SCORE_MIN <= score <= SCORE_MAX:
            raise DataError(
                f"{label}: '{field}' must be between {SCORE_MIN} and {SCORE_MAX}, "
                f"got {score}"
            )
        scores[field] = score

    beneficiaries = _require_positive_int(
        project["estimated_beneficiaries"],
        "estimated_beneficiaries",
        label,
    )
    improvement = _require_number(
        project["expected_improvement_pct"],
        "expected_improvement_pct",
        label,
    )
    if not SCORE_MIN <= improvement <= SCORE_MAX:
        raise DataError(
            f"{label}: 'expected_improvement_pct' must be between "
            f"{SCORE_MIN} and {SCORE_MAX}, got {improvement}"
        )

    return {
        "id": project["id"].strip(),
        "name": project["name"].strip(),
        "category": project["category"].strip(),
        "location": project["location"].strip(),
        "cost_cr": cost,
        "estimated_beneficiaries": beneficiaries,
        "expected_improvement_pct": improvement,
        **scores,
    }


def load_projects(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise DataError(f"Project data file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(raw, list) or not raw:
        raise DataError(f"{path} must contain a non-empty JSON array of projects")

    projects = [validate_project(item, index) for index, item in enumerate(raw, start=1)]

    ids = [project["id"] for project in projects]
    duplicates = sorted({project_id for project_id in ids if ids.count(project_id) > 1})
    if duplicates:
        raise DataError(f"Duplicate project id(s): {', '.join(duplicates)}")

    return projects


def component_contributions(project: dict[str, Any]) -> dict[str, float]:
    return {
        field: round(project[field] * weight, 2)
        for field, weight in WEIGHTS.items()
    }


def need_contributions(project: dict[str, Any]) -> dict[str, float]:
    return {
        field: round(project[field] * weight, 2)
        for field, weight in NEED_WEIGHTS.items()
    }


def priority_score(contributions: dict[str, float]) -> float:
    return round(sum(contributions.values()), 2)


def need_score(contributions: dict[str, float]) -> float:
    return round(sum(contributions.values()), 2)


def expected_impact(
    beneficiaries: int,
    need: float,
    improvement_pct: float,
) -> float:
    """People reached × need intensity × share of service gap closed."""
    return round(beneficiaries * (need / 100.0) * (improvement_pct / 100.0), 2)


def assert_impact_identity(project: dict[str, Any]) -> None:
    reconstructed = round(
        project["estimated_beneficiaries"]
        * project["need_score"]
        * project["expected_improvement_pct"]
        / 10000.0,
        2,
    )
    if reconstructed != project["expected_impact"]:
        raise DataError(
            f"{project['id']}: expected_impact {project['expected_impact']} "
            f"does not match beneficiaries × need_score × improvement / 10000 "
            f"= {reconstructed}"
        )


def score_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for project in projects:
        priority_parts = component_contributions(project)
        need_parts = need_contributions(project)
        need = need_score(need_parts)
        impact = expected_impact(
            project["estimated_beneficiaries"],
            need,
            project["expected_improvement_pct"],
        )
        row = {
            **project,
            "contributions": priority_parts,
            "need_contributions": need_parts,
            "priority_score": priority_score(priority_parts),
            "need_score": need,
            "expected_impact": impact,
        }
        assert_impact_identity(row)
        scored.append(row)

    scored.sort(key=lambda item: (-item["priority_score"], item["id"]))
    return scored


def _format_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
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


def print_report(scored: list[dict[str, Any]]) -> None:
    priority_weights = ", ".join(
        f"{field}={weight:.2f}" for field, weight in WEIGHTS.items()
    )
    need_weights = ", ".join(
        f"{field}={weight:.2f}" for field, weight in NEED_WEIGHTS.items()
    )
    print("CivicPrior — Project Scoring")
    print(f"Source: {DATA_PATH.relative_to(REPO_ROOT)}")
    print(f"priority_score weights: {priority_weights}")
    print(f"need_score weights:     {need_weights}")
    print("need_score excludes population_affected.")
    print()
    print("Legacy ranking by priority_score")
    print(
        _format_table(
            ("Rank", "Project", "Priority", "Need", "Impact", "Category", "Cost"),
            [
                (
                    str(rank),
                    project["name"],
                    f"{project['priority_score']:.2f}",
                    f"{project['need_score']:.2f}",
                    f"{project['expected_impact']:.2f}",
                    project["category"],
                    f"₹{project['cost_cr']:.0f} Cr",
                )
                for rank, project in enumerate(scored, start=1)
            ],
        )
    )
    print()
    print("Component contribution breakdown")
    print()

    for rank, project in enumerate(scored, start=1):
        print(
            f"{rank}. {project['name']} [{project['id']}]  "
            f"priority={project['priority_score']:.2f}  "
            f"need={project['need_score']:.2f}  "
            f"impact={project['expected_impact']:.2f}"
        )
        print("    priority_score")
        for field, weight in WEIGHTS.items():
            raw = project[field]
            contribution = project["contributions"][field]
            print(
                f"      {field:<24} {raw:>6.0f} × {weight:.2f} = {contribution:6.2f}"
            )
        print("    need_score")
        for field, weight in NEED_WEIGHTS.items():
            raw = project[field]
            contribution = project["need_contributions"][field]
            print(
                f"      {field:<24} {raw:>6.0f} × {weight:.2f} = {contribution:6.2f}"
            )
        print(
            "    expected_impact = "
            f"{project['estimated_beneficiaries']:,} × "
            f"({project['need_score']:.2f}/100) × "
            f"({project['expected_improvement_pct']:.0f}/100) = "
            f"{project['expected_impact']:.2f}"
        )
        print()


def main() -> int:
    priority_sum = round(sum(WEIGHTS.values()), 2)
    need_sum = round(sum(NEED_WEIGHTS.values()), 2)
    if priority_sum != 1.0:
        print(f"Internal error: priority weights sum to {priority_sum}, not 1.00", file=sys.stderr)
        return 1
    if need_sum != 1.0:
        print(f"Internal error: need weights sum to {need_sum}, not 1.00", file=sys.stderr)
        return 1

    try:
        projects = load_projects(DATA_PATH)
        scored = score_projects(projects)
    except DataError as exc:
        print(f"CivicPrior scoring failed: {exc}", file=sys.stderr)
        return 1

    print_report(scored)
    return 0


if __name__ == "__main__":
    sys.exit(main())
