"""Deterministic citizen-request clustering and deduplication (v0.1).

No embeddings. Cluster key is geo_id + category + requested_intervention.
Exact duplicates are identical normalized_english in the same geo/category.
Paraphrases share a cluster because they share the structured key.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

REQUESTS_DIR = Path(__file__).resolve().parent
if str(REQUESTS_DIR) not in sys.path:
    sys.path.insert(0, str(REQUESTS_DIR))

from mock_extractor import extract_seed_requests
from schema import GEO_CATALOG, REPO_ROOT, RequestError, DATA_PATH


URGENCY_RANK: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

CLUSTER_FIELDS: tuple[str, ...] = (
    "cluster_id",
    "geo_id",
    "category",
    "requested_intervention",
    "request_ids",
    "unique_request_ids",
    "duplicate_request_ids",
    "unique_request_count",
    "duplicate_request_count",
    "total_request_count",
    "urgency_counts",
    "max_urgency",
    "avg_confidence",
    "first_seen",
    "last_seen",
    "example_requests",
)

# Known gold groups used only for post-run validation, not for clustering.
EXPECTED_EXACT_DUPLICATES: tuple[tuple[str, str], ...] = (
    ("R001", "R004"),
    ("R026", "R028"),
)

EXPECTED_PARAPHRASE_GROUPS: dict[str, frozenset[str]] = {
    "Ward 17 distribution": frozenset({"R001", "R002", "R003", "R004", "R033"}),
    "Rural Block C pipeline": frozenset({"R005", "R006", "R007"}),
    "North Zone storage": frozenset({"R008", "R009", "R034"}),
    "East Zone treatment": frozenset({"R010", "R011", "R012"}),
    "Rural Block A PHC expansion": frozenset({"R013", "R014", "R015"}),
    "Village Cluster D sub-centre": frozenset({"R016", "R017", "R018"}),
    "Ward 9 PHC renovation": frozenset({"R019", "R020"}),
    "District periphery staffing": frozenset({"R021", "R022"}),
    "Village Cluster B connectivity": frozenset({"R023", "R024", "R025"}),
    "Central Zone expansion": frozenset({"R026", "R027", "R028"}),
    "South Zone resurfacing": frozenset({"R029", "R030", "R036"}),
    "Commercial District flyover": frozenset({"R031", "R032"}),
}


class ClusterError(Exception):
    """Clustering produced an inconsistent demand cluster."""


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sort_key(record: dict[str, Any]) -> tuple[datetime, str]:
    return (_parse_ts(record["submitted_at"]), record["id"])


def cluster_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (record["geo_id"], record["category"], record["requested_intervention"])


def make_cluster_id(geo_id: str, category: str, intervention: str) -> str:
    return f"cls_{geo_id}_{category}_{intervention}"


def duplicate_match_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        record["geo_id"],
        record["category"],
        record["normalized_english"],
    )


def mark_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag exact normalized_english copies in the same geo/category.

    The earliest submitted record (then lowest id) is canonical.
    Later copies remain in the dataset with is_duplicate=True.
    """
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[duplicate_match_key(record)].append(record)

    marked: list[dict[str, Any]] = []
    by_id = {record["id"]: record for record in records}
    duplicate_of: dict[str, str] = {}
    for members in groups.values():
        ordered = sorted(members, key=_sort_key)
        canonical_id = ordered[0]["id"]
        for copy in ordered[1:]:
            duplicate_of[copy["id"]] = canonical_id

    for record in records:
        row = dict(record)
        original_id = duplicate_of.get(record["id"])
        row["is_duplicate"] = original_id is not None
        row["duplicate_of"] = original_id
        if original_id:
            original = by_id[original_id]
            row["cluster_hint"] = cluster_key(original)
        marked.append(row)
    return marked


def _urgency_counts(unique_records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(record["urgency_class"] for record in unique_records)
    return {level: counts.get(level, 0) for level in URGENCY_RANK}


def _max_urgency(unique_records: list[dict[str, Any]]) -> str:
    return max(unique_records, key=lambda record: URGENCY_RANK[record["urgency_class"]])[
        "urgency_class"
    ]


def build_cluster(members: list[dict[str, Any]]) -> dict[str, Any]:
    if not members:
        raise ClusterError("Cannot build a cluster from zero requests")

    keys = {cluster_key(record) for record in members}
    if len(keys) != 1:
        raise ClusterError(f"Mixed cluster keys in one group: {keys}")

    geo_id, category, intervention = next(iter(keys))
    ordered = sorted(members, key=_sort_key)
    unique_members = [record for record in ordered if not record["is_duplicate"]]
    duplicate_members = [record for record in ordered if record["is_duplicate"]]
    if not unique_members:
        raise ClusterError(f"Cluster {geo_id}/{category}/{intervention} has no unique requests")

    examples = [
        {
            "id": record["id"],
            "language": record["language"],
            "urgency_class": record["urgency_class"],
            "normalized_english": record["normalized_english"],
        }
        for record in unique_members[:3]
    ]

    cluster = {
        "cluster_id": make_cluster_id(geo_id, category, intervention),
        "geo_id": geo_id,
        "canonical_location": GEO_CATALOG.get(geo_id, geo_id),
        "category": category,
        "requested_intervention": intervention,
        "request_ids": [record["id"] for record in ordered],
        "unique_request_ids": [record["id"] for record in unique_members],
        "duplicate_request_ids": [record["id"] for record in duplicate_members],
        "unique_request_count": len(unique_members),
        "duplicate_request_count": len(duplicate_members),
        "total_request_count": len(ordered),
        "urgency_counts": _urgency_counts(unique_members),
        "max_urgency": _max_urgency(unique_members),
        "avg_confidence": round(
            sum(record["confidence"] for record in unique_members) / len(unique_members),
            4,
        ),
        "first_seen": ordered[0]["submitted_at"],
        "last_seen": ordered[-1]["submitted_at"],
        "example_requests": examples,
    }
    missing = [field for field in CLUSTER_FIELDS if field not in cluster]
    if missing:
        raise ClusterError(f"Cluster missing fields: {', '.join(missing)}")
    if cluster["unique_request_count"] + cluster["duplicate_request_count"] != cluster[
        "total_request_count"
    ]:
        raise ClusterError("unique + duplicate counts must equal total_request_count")
    return cluster


def cluster_requests(records: list[dict[str, Any]]) -> dict[str, Any]:
    marked = mark_duplicates(records)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in marked:
        grouped[cluster_key(record)].append(record)

    clusters = [build_cluster(members) for members in grouped.values()]
    clusters.sort(
        key=lambda cluster: (
            -cluster["unique_request_count"],
            -cluster["total_request_count"],
            cluster["cluster_id"],
        )
    )

    unique_total = sum(cluster["unique_request_count"] for cluster in clusters)
    duplicate_total = sum(cluster["duplicate_request_count"] for cluster in clusters)
    return {
        "requests": marked,
        "clusters": clusters,
        "total_requests": len(marked),
        "total_clusters": len(clusters),
        "unique_request_count": unique_total,
        "duplicate_request_count": duplicate_total,
    }


def validate_gold_expectations(result: dict[str, Any]) -> list[str]:
    """Return human-readable pass/fail lines for known gold duplicate/paraphrase cases."""
    lines: list[str] = []
    by_id = {record["id"]: record for record in result["requests"]}
    cluster_of = {
        request_id: cluster["cluster_id"]
        for cluster in result["clusters"]
        for request_id in cluster["request_ids"]
    }

    for first_id, second_id in EXPECTED_EXACT_DUPLICATES:
        first = by_id[first_id]
        second = by_id[second_id]
        same_text = first["normalized_english"] == second["normalized_english"]
        same_place = first["geo_id"] == second["geo_id"] and first["category"] == second["category"]
        later = max((first, second), key=_sort_key)
        earlier = min((first, second), key=_sort_key)
        ok = (
            same_text
            and same_place
            and later["is_duplicate"]
            and later["duplicate_of"] == earlier["id"]
            and not earlier["is_duplicate"]
            and cluster_of[first_id] == cluster_of[second_id]
        )
        status = "PASS" if ok else "FAIL"
        lines.append(
            f"{status} exact duplicate {first_id}/{second_id}: "
            f"canonical={earlier['id']} duplicate={later['id']} "
            f"cluster={cluster_of[first_id]}"
        )

    for name, expected_ids in EXPECTED_PARAPHRASE_GROUPS.items():
        cluster_ids = {cluster_of[request_id] for request_id in expected_ids}
        ok = len(cluster_ids) == 1
        status = "PASS" if ok else "FAIL"
        lines.append(
            f"{status} paraphrase group '{name}': "
            f"{', '.join(sorted(expected_ids))} -> {', '.join(sorted(cluster_ids))}"
        )

    singleton = next(
        cluster
        for cluster in result["clusters"]
        if cluster["request_ids"] == ["R035"]
    )
    south = next(
        cluster
        for cluster in result["clusters"]
        if set(cluster["request_ids"]) == {"R029", "R030", "R036"}
    )
    ward9_health = next(
        cluster
        for cluster in result["clusters"]
        if set(cluster["request_ids"]) == {"R019", "R020"}
    )
    lines.append(
        f"INFO R035 stays a singleton ({singleton['cluster_id']}); "
        f"not merged with {south['cluster_id']} or {ward9_health['cluster_id']}"
    )
    return lines


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


def _mix(values: list[str]) -> str:
    counts = Counter(values)
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def print_report(result: dict[str, Any]) -> None:
    clusters = result["clusters"]
    print("CivicPrior — Demand Clustering (deterministic v0.1)")
    print(f"Source: {DATA_PATH.relative_to(REPO_ROOT)}")
    print("Cluster key: geo_id + category + requested_intervention")
    print("Duplicates: identical normalized_english in the same geo_id + category")
    print("No embeddings. No Gemini.")
    print()
    print(f"Total requests:     {result['total_requests']}")
    print(f"Unique requests:    {result['unique_request_count']}")
    print(f"Duplicate requests: {result['duplicate_request_count']}")
    print(f"Demand clusters:    {result['total_clusters']}")
    print(f"Category mix:       {_mix([cluster['category'] for cluster in clusters])}")
    print(
        f"Geography mix:      {_mix([cluster['canonical_location'] for cluster in clusters])}"
    )
    print()
    print("Clusters by unique demand (largest first)")
    print(
        _format_table(
            (
                "#",
                "Cluster ID",
                "Geo",
                "Category",
                "Intervention",
                "Unique",
                "Dups",
                "Total",
                "Max urgency",
                "Request IDs",
            ),
            [
                (
                    str(index),
                    cluster["cluster_id"],
                    cluster["canonical_location"],
                    cluster["category"],
                    cluster["requested_intervention"],
                    str(cluster["unique_request_count"]),
                    str(cluster["duplicate_request_count"]),
                    str(cluster["total_request_count"]),
                    cluster["max_urgency"],
                    ", ".join(cluster["request_ids"]),
                )
                for index, cluster in enumerate(clusters, start=1)
            ],
        )
    )
    print()
    print("Largest 5 clusters")
    for cluster in clusters[:5]:
        dup = ", ".join(cluster["duplicate_request_ids"]) or "(none)"
        print(
            f"- {cluster['cluster_id']}: unique={cluster['unique_request_count']} "
            f"dups={cluster['duplicate_request_count']} total={cluster['total_request_count']} "
            f"max_urgency={cluster['max_urgency']} avg_conf={cluster['avg_confidence']:.2f}"
        )
        print(f"    ids: {', '.join(cluster['request_ids'])}")
        print(f"    duplicates: {dup}")
        print(f"    example: {cluster['example_requests'][0]['normalized_english']}")
    print()
    print("Gold-set validation")
    for line in validate_gold_expectations(result):
        print(f"  {line}")


def main() -> int:
    try:
        records = extract_seed_requests()
        result = cluster_requests(records)
        failures = [
            line for line in validate_gold_expectations(result) if line.startswith("FAIL")
        ]
    except (RequestError, ClusterError) as exc:
        print(f"CivicPrior clustering failed: {exc}", file=sys.stderr)
        return 1

    print_report(result)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
