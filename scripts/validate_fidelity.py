"""Source-fidelity gate: locator ownership, table shape, and typed counts.

Checks that every record's locator starts at its printed identity, that raw
table text matches the physical source span byte for byte, that typed
sub-records stay inside their owning section span, that catalog counts match
the reviewed inventory, and that rights metadata is preserved exactly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fitdlib import (
    ATTRIBUTION_STATEMENT,
    MANIFEST_NAME,
    SOURCE_FILE,
    clean_heading,
    iter_object_files,
    load_json,
)

EXPECTED_COUNTS = {
    "actions": 12,
    "entanglements": 12,
    "downtime-activities": 6,
    "trauma-conditions": 8,
}
EXPECTED_ABILITIES = {"character": 42, "crew": 16}
EXPECTED_CLAIMS = {"crew": 29, "prison": 6}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()

    errors = []
    counts = {}
    ability_scopes = {}
    claim_types = {}
    rule_spans = {}
    sub_records = []

    records = [
        (collection, load_json(path))
        for collection, path in iter_object_files(root)
    ]

    for collection, record in records:
        if collection == "sources":
            continue
        counts[collection] = counts.get(collection, 0) + 1
        locator = record["sourceLocator"]
        start_line = lines[locator["lineStart"] - 1]
        if collection == "tables":
            # Table locators start at the physical source table.
            if not start_line.lstrip().startswith("|"):
                errors.append(
                    f"{record['slug']}: table locator does not start at a "
                    f"table line ({locator['lineStart']})"
                )
        elif record["name"] not in clean_heading(start_line):
            errors.append(
                f"{record['slug']}: name {record['name']!r} not on locator "
                f"start line {locator['lineStart']}"
            )
        if collection == "rules":
            rule_spans[locator["section"]] = (
                locator["lineStart"],
                locator["lineEnd"],
            )
        if collection == "tables":
            span = "\n".join(
                lines[locator["lineStart"] - 1 : locator["lineEnd"]]
            )
            if record["rawText"] != span:
                errors.append(f"{record['slug']}: rawText differs from source span")
            if not record["rows"]:
                errors.append(f"{record['slug']}: table has no rows")
        if collection == "actions":
            if "attribute" not in record:
                errors.append(f"{record['slug']}: action missing attribute")
            sub_records.append(record)
        if collection == "special-abilities":
            scope = record.get("abilityScope", "")
            ability_scopes[scope] = ability_scopes.get(scope, 0) + 1
        if collection == "claims":
            claim_type = record.get("claimType", "")
            claim_types[claim_type] = claim_types.get(claim_type, 0) + 1
            if claim_type == "crew":
                sub_records.append(record)
        if collection == "trauma-conditions":
            sub_records.append(record)

    # Paragraph/bullet-grained records must sit inside the rule that owns
    # their section.
    for record in sub_records:
        locator = record["sourceLocator"]
        owner = rule_spans.get(locator["section"])
        if owner is None:
            errors.append(f"{record['slug']}: no owning rule for §{locator['section']}")
        elif not (owner[0] <= locator["lineStart"] <= locator["lineEnd"] <= owner[1]):
            errors.append(f"{record['slug']}: span escapes owning rule §{locator['section']}")

    for collection, expected in EXPECTED_COUNTS.items():
        if counts.get(collection, 0) != expected:
            errors.append(
                f"{collection}: expected {expected} records, found {counts.get(collection, 0)}"
            )
    if ability_scopes != EXPECTED_ABILITIES:
        errors.append(f"special-abilities: scope counts {ability_scopes} != {EXPECTED_ABILITIES}")
    if claim_types != EXPECTED_CLAIMS:
        errors.append(f"claims: type counts {claim_types} != {EXPECTED_CLAIMS}")

    source_records = [r for c, r in records if c == "sources"]
    if len(source_records) != 1:
        errors.append(f"expected one source record, found {len(source_records)}")
    else:
        source = source_records[0]
        if source.get("attributionStatement") != ATTRIBUTION_STATEMENT:
            errors.append("source record attribution statement differs")
        if source.get("license") != "CC-BY-3.0":
            errors.append("source record license is not CC-BY-3.0")
    manifest = load_json(root / "objects" / MANIFEST_NAME)
    if manifest["metadata"].get("attributionStatement") != ATTRIBUTION_STATEMENT:
        errors.append("manifest attribution statement differs")
    if ATTRIBUTION_STATEMENT not in (root / "llms-full.txt").read_text(encoding="utf-8"):
        errors.append("llms-full.txt missing the attribution statement")

    if errors:
        print("\n".join(errors[:50]))
        print(f"FAIL: {len(errors)} fidelity errors")
        sys.exit(1)
    print(
        f"fidelity: {sum(counts.values())} records anchored to their printed "
        "identity; tables, sub-spans, counts, and rights metadata verified"
    )


if __name__ == "__main__":
    main()
