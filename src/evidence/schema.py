"""CivicPrior synthetic evidence schemas (v0.1).

These records are demo evidence, not live government datasets.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GEO_PROFILES_PATH = REPO_ROOT / "data" / "seed-geo-profiles.json"
INFRA_METRICS_PATH = REPO_ROOT / "data" / "seed-infrastructure-metrics.json"
INVESTMENT_PLANS_PATH = REPO_ROOT / "data" / "seed-investment-plans.json"

CATEGORIES: frozenset[str] = frozenset({"water", "healthcare", "roads"})
URBAN_RURAL: frozenset[str] = frozenset({"urban", "rural", "peri_urban"})
INVESTMENT_STATUSES: frozenset[str] = frozenset(
    {"planned", "approved", "in_progress", "completed"}
)
ACTIVE_INVESTMENT_STATUSES: frozenset[str] = frozenset({"approved", "in_progress"})
CANONICAL_GEO_IDS: frozenset[str] = frozenset(
    {
        "geo_ward_17",
        "geo_ward_9",
        "geo_central_zone",
        "geo_north_zone",
        "geo_south_zone",
        "geo_east_zone",
        "geo_commercial_district",
        "geo_rural_block_a",
        "geo_rural_block_c",
        "geo_village_cluster_b",
        "geo_village_cluster_d",
        "geo_district_periphery",
    }
)

GEO_PROFILE_FIELDS: tuple[str, ...] = (
    "geo_id",
    "location_name",
    "population",
    "vulnerability_index",
    "remoteness_index",
    "urban_rural",
    "synthetic",
)
INFRA_METRIC_FIELDS: tuple[str, ...] = (
    "id",
    "geo_id",
    "category",
    "service_coverage_pct",
    "service_quality_score",
    "infrastructure_deficit_score",
    "source_type",
    "synthetic",
)
INVESTMENT_FIELDS: tuple[str, ...] = (
    "id",
    "geo_id",
    "category",
    "project_name",
    "amount_cr",
    "status",
    "start_date",
    "synthetic",
)

SCORE_MIN = 0
SCORE_MAX = 100


class EvidenceError(Exception):
    """Malformed or incomplete evidence data."""


def _label(raw: Any, index: int, kind: str) -> str:
    if isinstance(raw, dict):
        record_id = raw.get("id") or raw.get("geo_id")
        if isinstance(record_id, str) and record_id.strip():
            return f"{kind} {index} ({record_id.strip()})"
    return f"{kind} {index}"


def _require_nonempty_str(value: Any, field: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{label}: '{field}' must be a non-empty string")
    return value.strip()


def _require_enum(value: Any, field: str, allowed: frozenset[str], label: str) -> str:
    text = _require_nonempty_str(value, field, label)
    if text not in allowed:
        raise EvidenceError(
            f"{label}: '{field}' must be one of [{', '.join(sorted(allowed))}], got {text!r}"
        )
    return text


def _require_number(value: Any, field: str, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{label}: '{field}' must be a number, got {value!r}")
    return float(value)


def _require_score(value: Any, field: str, label: str) -> float:
    score = _require_number(value, field, label)
    if not SCORE_MIN <= score <= SCORE_MAX:
        raise EvidenceError(
            f"{label}: '{field}' must be between {SCORE_MIN} and {SCORE_MAX}, got {score}"
        )
    return score


def _require_positive_int(value: Any, field: str, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceError(f"{label}: '{field}' must be an integer, got {value!r}")
    if value <= 0:
        raise EvidenceError(f"{label}: '{field}' must be > 0, got {value}")
    return value


def _require_synthetic(raw: dict[str, Any], label: str) -> None:
    if raw.get("synthetic") is not True:
        raise EvidenceError(f"{label}: evidence records must set synthetic=true")


def _require_geo_id(value: Any, label: str) -> str:
    geo_id = _require_enum(value, "geo_id", CANONICAL_GEO_IDS, label)
    return geo_id


def _load_json_array(path: Path, kind: str) -> list[Any]:
    if not path.is_file():
        raise EvidenceError(f"{kind} file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise EvidenceError(f"{path} must contain a non-empty JSON array")
    return raw


def validate_geo_profile(raw: Any, index: int) -> dict[str, Any]:
    label = _label(raw, index, "geo profile")
    if not isinstance(raw, dict):
        raise EvidenceError(f"{label}: expected an object")
    missing = [field for field in GEO_PROFILE_FIELDS if field not in raw]
    if missing:
        raise EvidenceError(f"{label}: missing {', '.join(missing)}")
    _require_synthetic(raw, label)
    return {
        "geo_id": _require_geo_id(raw["geo_id"], label),
        "location_name": _require_nonempty_str(raw["location_name"], "location_name", label),
        "population": _require_positive_int(raw["population"], "population", label),
        "vulnerability_index": _require_score(
            raw["vulnerability_index"], "vulnerability_index", label
        ),
        "remoteness_index": _require_score(raw["remoteness_index"], "remoteness_index", label),
        "urban_rural": _require_enum(raw["urban_rural"], "urban_rural", URBAN_RURAL, label),
        "synthetic": True,
    }


def validate_infra_metric(raw: Any, index: int) -> dict[str, Any]:
    label = _label(raw, index, "infrastructure metric")
    if not isinstance(raw, dict):
        raise EvidenceError(f"{label}: expected an object")
    missing = [field for field in INFRA_METRIC_FIELDS if field not in raw]
    if missing:
        raise EvidenceError(f"{label}: missing {', '.join(missing)}")
    _require_synthetic(raw, label)
    return {
        "id": _require_nonempty_str(raw["id"], "id", label),
        "geo_id": _require_geo_id(raw["geo_id"], label),
        "category": _require_enum(raw["category"], "category", CATEGORIES, label),
        "service_coverage_pct": _require_score(
            raw["service_coverage_pct"], "service_coverage_pct", label
        ),
        "service_quality_score": _require_score(
            raw["service_quality_score"], "service_quality_score", label
        ),
        "infrastructure_deficit_score": _require_score(
            raw["infrastructure_deficit_score"], "infrastructure_deficit_score", label
        ),
        "source_type": _require_nonempty_str(raw["source_type"], "source_type", label),
        "synthetic": True,
    }


def validate_investment_plan(raw: Any, index: int) -> dict[str, Any]:
    label = _label(raw, index, "investment plan")
    if not isinstance(raw, dict):
        raise EvidenceError(f"{label}: expected an object")
    missing = [field for field in INVESTMENT_FIELDS if field not in raw]
    if missing:
        raise EvidenceError(f"{label}: missing {', '.join(missing)}")
    _require_synthetic(raw, label)
    start = _require_nonempty_str(raw["start_date"], "start_date", label)
    try:
        date.fromisoformat(start)
    except ValueError as exc:
        raise EvidenceError(f"{label}: 'start_date' must be YYYY-MM-DD, got {start!r}") from exc
    amount = _require_number(raw["amount_cr"], "amount_cr", label)
    if amount < 0:
        raise EvidenceError(f"{label}: 'amount_cr' must be >= 0, got {amount}")
    return {
        "id": _require_nonempty_str(raw["id"], "id", label),
        "geo_id": _require_geo_id(raw["geo_id"], label),
        "category": _require_enum(raw["category"], "category", CATEGORIES, label),
        "project_name": _require_nonempty_str(raw["project_name"], "project_name", label),
        "amount_cr": amount,
        "status": _require_enum(raw["status"], "status", INVESTMENT_STATUSES, label),
        "start_date": start,
        "synthetic": True,
    }


def _reject_duplicate_ids(records: list[dict[str, Any]], field: str, kind: str) -> None:
    ids = [record[field] for record in records]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise EvidenceError(f"Duplicate {kind} id(s): {', '.join(duplicates)}")


def load_geo_profiles(path: Path = GEO_PROFILES_PATH) -> dict[str, dict[str, Any]]:
    records = [
        validate_geo_profile(item, index)
        for index, item in enumerate(_load_json_array(path, "geo profiles"), start=1)
    ]
    _reject_duplicate_ids(records, "geo_id", "geo profile")
    missing = sorted(CANONICAL_GEO_IDS - {record["geo_id"] for record in records})
    if missing:
        raise EvidenceError(f"Geo profiles missing canonical geo_id(s): {', '.join(missing)}")
    return {record["geo_id"]: record for record in records}


def load_infra_metrics(path: Path = INFRA_METRICS_PATH) -> dict[tuple[str, str], dict[str, Any]]:
    records = [
        validate_infra_metric(item, index)
        for index, item in enumerate(_load_json_array(path, "infrastructure metrics"), start=1)
    ]
    _reject_duplicate_ids(records, "id", "infrastructure metric")
    keyed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["geo_id"], record["category"])
        if key in keyed:
            raise EvidenceError(
                f"Duplicate infrastructure metric for {record['geo_id']} / {record['category']}"
            )
        keyed[key] = record
    return keyed


def load_investment_plans(path: Path = INVESTMENT_PLANS_PATH) -> list[dict[str, Any]]:
    records = [
        validate_investment_plan(item, index)
        for index, item in enumerate(_load_json_array(path, "investment plans"), start=1)
    ]
    _reject_duplicate_ids(records, "id", "investment plan")
    return records


def investment_gap_score(active_amount_cr: float) -> int:
    if active_amount_cr <= 0:
        return 100
    if active_amount_cr < 10:
        return 75
    if active_amount_cr <= 20:
        return 50
    return 25
