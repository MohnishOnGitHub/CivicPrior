"""CivicPrior citizen-request schema (v0.1).

Structured demand records produced from raw multilingual requests.
Category values match seed-projects.json so later joins stay simple.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "data" / "seed-citizen-requests.json"

CATEGORIES: frozenset[str] = frozenset({"water", "healthcare", "roads"})

LANGUAGES: frozenset[str] = frozenset({"en", "hi", "te"})

URGENCY_CLASSES: frozenset[str] = frozenset({"low", "medium", "high", "critical"})

SUBCATEGORIES_BY_CATEGORY: dict[str, frozenset[str]] = {
    "water": frozenset(
        {
            "supply_reliability",
            "water_quality",
            "piped_access",
            "storage_capacity",
        }
    ),
    "healthcare": frozenset(
        {
            "facility_capacity",
            "staffing",
            "local_access",
            "service_quality",
        }
    ),
    "roads": frozenset(
        {
            "all_weather_connectivity",
            "congestion",
            "pavement_condition",
            "junction_bottleneck",
        }
    ),
}

INTERVENTIONS_BY_CATEGORY: dict[str, frozenset[str]] = {
    "water": frozenset(
        {
            "water_distribution_upgrade",
            "municipal_water_storage_expansion",
            "rural_drinking_water_pipeline",
            "water_treatment_plant_upgrade",
        }
    ),
    "healthcare": frozenset(
        {
            "rural_phc_expansion",
            "phc_renovation",
            "community_health_subcentre",
            "district_phc_staffing_upgrade",
        }
    ),
    "roads": frozenset(
        {
            "urban_road_expansion",
            "village_road_connectivity",
            "urban_flyover_improvement",
            "main_road_resurfacing",
        }
    ),
}

# Canonical geos from the v0.1 seed project locations.
GEO_CATALOG: dict[str, str] = {
    "geo_ward_17": "Ward 17",
    "geo_ward_9": "Ward 9",
    "geo_central_zone": "Central Zone",
    "geo_north_zone": "North Zone",
    "geo_south_zone": "South Zone",
    "geo_east_zone": "East Zone",
    "geo_commercial_district": "Commercial District",
    "geo_rural_block_a": "Rural Block A",
    "geo_rural_block_c": "Rural Block C",
    "geo_village_cluster_b": "Village Cluster B",
    "geo_village_cluster_d": "Village Cluster D",
    "geo_district_periphery": "District Periphery",
}

REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "original_text",
    "language",
    "normalized_english",
    "category",
    "subcategory",
    "location_text",
    "geo_id",
    "urgency_class",
    "requested_intervention",
    "confidence",
    "submitted_at",
    "synthetic",
)

AMBIGUOUS_CONFIDENCE_MAX = 0.70


class RequestError(Exception):
    """Malformed citizen-request data."""


def _label(raw: Any, index: int) -> str:
    if isinstance(raw, dict):
        request_id = raw.get("id")
        if isinstance(request_id, str) and request_id.strip():
            return f"request {index} ({request_id.strip()})"
    return f"request {index}"


def _require_nonempty_str(value: Any, field: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"{label}: '{field}' must be a non-empty string")
    return value.strip()


def _require_enum(value: Any, field: str, allowed: frozenset[str], label: str) -> str:
    text = _require_nonempty_str(value, field, label)
    if text not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise RequestError(f"{label}: '{field}' must be one of [{allowed_list}], got {text!r}")
    return text


def _require_confidence(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RequestError(f"{label}: 'confidence' must be a number, got {value!r}")
    score = float(value)
    if score != score or not 0.0 <= score <= 1.0:
        raise RequestError(f"{label}: 'confidence' must be between 0 and 1, got {score}")
    return score


def _require_timestamp(value: Any, label: str) -> str:
    text = _require_nonempty_str(value, "submitted_at", label)
    iso = text.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(iso)
    except ValueError as exc:
        raise RequestError(
            f"{label}: 'submitted_at' must be an ISO-8601 datetime, got {text!r}"
        ) from exc
    return text


def validate_request(raw: Any, index: int) -> dict[str, Any]:
    label = _label(raw, index)
    if not isinstance(raw, dict):
        raise RequestError(f"{label}: expected an object, got {type(raw).__name__}")

    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        raise RequestError(f"{label}: missing required field(s): {', '.join(missing)}")

    if raw["synthetic"] is not True:
        raise RequestError(f"{label}: seed requests must set synthetic=true")

    category = _require_enum(raw["category"], "category", CATEGORIES, label)
    subcategory = _require_enum(
        raw["subcategory"],
        "subcategory",
        SUBCATEGORIES_BY_CATEGORY[category],
        label,
    )
    intervention = _require_enum(
        raw["requested_intervention"],
        "requested_intervention",
        INTERVENTIONS_BY_CATEGORY[category],
        label,
    )
    geo_id = _require_nonempty_str(raw["geo_id"], "geo_id", label)
    if geo_id not in GEO_CATALOG:
        allowed = ", ".join(sorted(GEO_CATALOG))
        raise RequestError(f"{label}: 'geo_id' must be one of [{allowed}], got {geo_id!r}")

    return {
        "id": _require_nonempty_str(raw["id"], "id", label),
        "original_text": _require_nonempty_str(raw["original_text"], "original_text", label),
        "language": _require_enum(raw["language"], "language", LANGUAGES, label),
        "normalized_english": _require_nonempty_str(
            raw["normalized_english"], "normalized_english", label
        ),
        "category": category,
        "subcategory": subcategory,
        "location_text": _require_nonempty_str(raw["location_text"], "location_text", label),
        "geo_id": geo_id,
        "canonical_location": GEO_CATALOG[geo_id],
        "urgency_class": _require_enum(
            raw["urgency_class"], "urgency_class", URGENCY_CLASSES, label
        ),
        "requested_intervention": intervention,
        "confidence": _require_confidence(raw["confidence"], label),
        "submitted_at": _require_timestamp(raw["submitted_at"], label),
        "synthetic": True,
    }


def load_requests(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RequestError(f"Citizen-request file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RequestError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, list) or not raw:
        raise RequestError(f"{path} must contain a non-empty JSON array of requests")

    records = [validate_request(item, index) for index, item in enumerate(raw, start=1)]
    ids = [record["id"] for record in records]
    duplicates = sorted({request_id for request_id in ids if ids.count(request_id) > 1})
    if duplicates:
        raise RequestError(f"Duplicate request id(s): {', '.join(duplicates)}")
    return records


def is_ambiguous(record: dict[str, Any]) -> bool:
    return record["confidence"] < AMBIGUOUS_CONFIDENCE_MAX
