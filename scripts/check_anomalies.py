"""Fail when a source-anomaly hit lacks an explicit reviewed disposition.

Each registry entry in objects/sources/extraction-overrides.json pins a
detector pattern to an expected number of remaining hits against the current
source digest. A new, moved, or removed hit fails the gate until a person
reviews it.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fitdlib import SOURCE_FILE, load_json

REQUIRED_FIELDS = (
    "id",
    "pattern",
    "expectedRemaining",
    "observed",
    "disposition",
    "rationale",
    "status",
)
REQUIRED_OVERRIDE_FIELDS = (
    "id",
    "kind",
    "observed",
    "treatAs",
    "scope",
    "rationale",
    "status",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    text = (root / SOURCE_FILE).read_text(encoding="utf-8")
    registry = load_json(root / "objects/sources/extraction-overrides.json")
    errors = []
    total = 0
    identifiers = []
    for review in registry.get("anomalyReviews", []):
        identifiers.append(review.get("id"))
        for required in REQUIRED_FIELDS:
            if required not in review:
                errors.append(
                    f"{review.get('id', '<unknown>')}: missing registry field {required}"
                )
        hits = list(re.finditer(review["pattern"], text, re.MULTILINE))
        total += len(hits)
        expected = review["expectedRemaining"]
        if review["status"] not in ("resolved", "false-positive"):
            errors.append(f"{review['id']}: unreviewed status {review['status']!r}")
        if len(hits) != expected:
            lines = [text.count("\n", 0, hit.start()) + 1 for hit in hits[:8]]
            errors.append(
                f"{review['id']}: expected {expected} remaining hits, found {len(hits)}"
                + (f" at lines {lines}" if lines else "")
            )
    for override in registry.get("overrides", []):
        identifiers.append(override.get("id"))
        for required in REQUIRED_OVERRIDE_FIELDS:
            if required not in override:
                errors.append(
                    f"{override.get('id', '<unknown>')}: missing override "
                    f"field {required}"
                )
        if override.get("kind") in (
            "heading-level",
            "table-header-separator",
        ) and not isinstance(override.get("line"), int):
            errors.append(
                f"{override.get('id', '<unknown>')}: line-pinned override "
                "is missing an integer line"
            )
        if override.get("status") != "applied-in-extraction":
            errors.append(
                f"{override.get('id', '<unknown>')}: unreviewed override status "
                f"{override.get('status')!r}"
            )
    duplicates = sorted(
        identifier
        for identifier in set(identifiers)
        if identifier is not None and identifiers.count(identifier) > 1
    )
    if duplicates:
        errors.append(f"duplicate anomaly/override ids: {duplicates}")
    if errors:
        print("\n".join(errors))
        print("FAIL: anomaly registry is stale or incomplete")
        sys.exit(1)
    print(
        f"anomalies: {len(registry.get('anomalyReviews', []))} reviewed detectors, "
        f"{total} allowed source hits"
    )


if __name__ == "__main__":
    main()
