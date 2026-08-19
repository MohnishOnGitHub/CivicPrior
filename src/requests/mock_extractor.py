"""Mock structured extraction for CivicPrior citizen requests.

v0.1 does not call Gemini. Synthetic seed records already carry gold
structured fields; this module loads, validates, and prints them so the
downstream pipeline can be tested without an external API.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

REQUESTS_DIR = Path(__file__).resolve().parent
if str(REQUESTS_DIR) not in sys.path:
    sys.path.insert(0, str(REQUESTS_DIR))

from schema import (
    AMBIGUOUS_CONFIDENCE_MAX,
    DATA_PATH,
    GEO_CATALOG,
    REPO_ROOT,
    RequestError,
    is_ambiguous,
    load_requests,
)


def extract_seed_requests(path: Path = DATA_PATH) -> list[dict[str, Any]]:
    """Deterministically map seed requests into the validated schema."""
    return load_requests(path)


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


def print_report(records: list[dict[str, Any]]) -> None:
    languages = [record["language"] for record in records]
    categories = [record["category"] for record in records]
    urgencies = [record["urgency_class"] for record in records]
    geos = [record["geo_id"] for record in records]
    ambiguous = [record for record in records if is_ambiguous(record)]

    print("CivicPrior — Citizen Request Intake (mock extractor)")
    print(f"Source: {DATA_PATH.relative_to(REPO_ROOT)}")
    print("All records are synthetic. No Gemini call was made.")
    print()
    print(f"Requests:     {len(records)}")
    print(f"Languages:    {_mix(languages)}")
    print(f"Categories:   {_mix(categories)}")
    print(f"Urgency:      {_mix(urgencies)}")
    print(f"Geographies:  {len(set(geos))} of {len(GEO_CATALOG)} catalog geos used")
    print(
        f"Ambiguous:    {len(ambiguous)} with confidence < {AMBIGUOUS_CONFIDENCE_MAX:.2f}"
    )
    print()
    print("Normalized requests")
    print(
        _format_table(
            (
                "ID",
                "Lang",
                "Category",
                "Subcategory",
                "Geo",
                "Urgency",
                "Intervention",
                "Conf",
                "Normalized English",
            ),
            [
                (
                    record["id"],
                    record["language"],
                    record["category"],
                    record["subcategory"],
                    record["geo_id"],
                    record["urgency_class"],
                    record["requested_intervention"],
                    f"{record['confidence']:.2f}",
                    record["normalized_english"],
                )
                for record in records
            ],
        )
    )
    print()
    print("Original text")
    for record in records:
        print(f"{record['id']} [{record['language']}] {record['original_text']}")
    print()
    if ambiguous:
        print("Ambiguous / low-confidence extractions")
        print(
            "(mock still assigned a deterministic category; a live extractor should flag these for review)"
        )
        print()
        print(
            _format_table(
                ("ID", "Conf", "Assigned category", "Assigned intervention", "Why it is ambiguous"),
                [
                    (
                        record["id"],
                        f"{record['confidence']:.2f}",
                        record["category"],
                        record["requested_intervention"],
                        record["normalized_english"],
                    )
                    for record in ambiguous
                ],
            )
        )
    else:
        print("Ambiguous / low-confidence extractions: (none)")


def main() -> int:
    try:
        records = extract_seed_requests()
    except RequestError as exc:
        print(f"CivicPrior request intake failed: {exc}", file=sys.stderr)
        return 1
    print_report(records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
