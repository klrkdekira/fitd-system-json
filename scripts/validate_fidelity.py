"""Prove physical provenance and exact source-to-record extraction fidelity.

This gate independently reconstructs the source section inventory and the
documented extraction transforms. It checks exact rule/catalog prose, every
typed sub-span, every physical table and parsed cell, catalog classification,
locator ownership, typed inventories, and required rights statements.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from fitdlib import (
    ACTIONS_CHAPTER,
    ACTIONS_HEADING,
    ATTRIBUTES,
    ATTRIBUTION_STATEMENT,
    CHARACTER_ABILITIES_HEADING,
    CONVERSION_STATEMENT,
    CREW_ABILITIES_HEADING,
    CREW_CLAIMS_HEADING,
    DOWNTIME_ACTIVITY_NAMES,
    DOWNTIME_CHAPTER,
    ENTANGLEMENTS_CHAPTER,
    MANIFEST_NAME,
    PLANS_CHAPTER,
    PRISON_CLAIM_EXCLUDE,
    PRISON_CLAIMS_HEADING,
    SOURCE_FILE,
    TEAMWORK_HEADING,
    TRAUMA_HEADING,
    VICE_HEADING,
    clean_heading,
    iter_object_files,
    load_json,
)

HEADING_RE = re.compile(r"^(#{1,6}) (.+?)\s*$")
TABLE_LINE_RE = re.compile(r"^\|.*\|\s*$")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
ACTION_RE = re.compile(r"^When you \*\*(\w+)\*\*, .*")
BOLD_LEAD_RE = re.compile(r"^\*\*([^*]+?)\*\*")
BOLD_BULLET_RE = re.compile(r"^\* \*\*([^*]+?)\*\*: .*")
PLAN_BULLET_RE = re.compile(r"^\* (\w+) - .+ \*Detail: (.+)\*$")

EXPECTED_COUNTS = {
    "rules": 202,
    "tables": 15,
    "actions": 12,
    "entanglements": 12,
    "downtime-activities": 6,
    "trauma-conditions": 8,
    "vices": 7,
    "plans": 6,
    "teamwork-maneuvers": 4,
}
EXPECTED_ABILITIES = {"character": 42, "crew": 16}
EXPECTED_CLAIMS = {"crew": 29, "prison": 6}


def optional_text(record, field, expected, errors):
    """Compare an optional emitted prose field with its exact expectation."""
    actual = record.get(field)
    if expected:
        if actual != expected:
            errors.append(f"{record['slug']}: {field} differs from source")
    elif field in record:
        errors.append(f"{record['slug']}: unexpected empty {field}")


def source_sections(lines, heading_overrides, errors):
    """Independently reconstruct physical sections and their hierarchy."""
    sections = []
    stack = []
    seen_overrides = set()
    for line_number, raw in enumerate(lines, start=1):
        match = HEADING_RE.match(raw)
        if not match:
            continue
        level, title = len(match.group(1)), match.group(2)
        override = heading_overrides.get(line_number)
        if override:
            seen_overrides.add(line_number)
            if raw.rstrip() != override["observed"]:
                errors.append(
                    f"heading override at line {line_number} expected "
                    f"{override['observed']!r}, found {raw.rstrip()!r}"
                )
            treated = HEADING_RE.match(override["treatAs"])
            if not treated:
                errors.append(
                    f"heading override at line {line_number} has invalid treatAs"
                )
            else:
                level, title = len(treated.group(1)), treated.group(2)
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        section = {
            "level": level,
            "name": clean_heading(title),
            "lineStart": line_number,
            "parent": stack[-1] if stack else None,
        }
        section["chapter"] = (
            section if level == 1 else (stack[0] if stack else None)
        )
        sections.append(section)
        stack.append(section)

    unused = set(heading_overrides) - seen_overrides
    if unused:
        errors.append(f"heading overrides do not target headings: {sorted(unused)}")

    chapter_ordinal = 0
    within_chapter = 0
    for index, section in enumerate(sections):
        last = (
            sections[index + 1]["lineStart"] - 1
            if index + 1 < len(sections)
            else len(lines)
        )
        while last > section["lineStart"] and not lines[last - 1].strip():
            last -= 1
        section["lineEnd"] = last
        if section["level"] == 1:
            chapter_ordinal += 1
            within_chapter = 0
        within_chapter += 1
        section["section"] = f"{chapter_ordinal}.{within_chapter}"
    return sections


def expected_collection(section):
    """Return the collection selected by the documented section grammar."""
    parent = section["parent"]
    if parent and parent["name"] in (
        CHARACTER_ABILITIES_HEADING,
        CREW_ABILITIES_HEADING,
    ):
        return "special-abilities"
    if (
        section["level"] == 3
        and parent
        and parent["level"] == 1
        and parent["name"] == ENTANGLEMENTS_CHAPTER
    ):
        return "entanglements"
    if (
        section["level"] == 3
        and parent
        and parent["level"] == 1
        and parent["name"] == DOWNTIME_CHAPTER
        and section["name"].lower()
        in {name.lower() for name in DOWNTIME_ACTIVITY_NAMES}
    ):
        return "downtime-activities"
    if (
        section["level"] == 3
        and parent
        and parent["name"] == PRISON_CLAIMS_HEADING
        and section["name"] not in PRISON_CLAIM_EXCLUDE
    ):
        return "claims"
    if (
        section["level"] == 3
        and parent
        and parent["level"] == 2
        and parent["name"] == TEAMWORK_HEADING
    ):
        return "teamwork-maneuvers"
    return "rules"


def body_lines(lines, section):
    return lines[section["lineStart"] : section["lineEnd"]]


def expected_rule_text(lines, section):
    kept = [
        line
        for line in body_lines(lines, section)
        if not TABLE_LINE_RE.match(line) and line.strip() != "---"
    ]
    return "\n".join(kept).strip("\n").strip()


def expected_catalog_text(lines, section):
    prose = []
    commentary = []
    for line in body_lines(lines, section):
        if line.startswith(">"):
            commentary.append(line[1:].lstrip() if len(line) > 1 else "")
        elif line.strip() != "---":
            prose.append(line)
    return (
        "\n".join(prose).strip("\n").strip(),
        "\n".join(commentary).strip("\n").strip(),
    )


def split_table_row(line):
    """Split cells while preserving Markdown-escaped pipe characters."""
    content = line.strip().strip("|")
    cells = []
    cell = []
    for index, character in enumerate(content):
        if character == "|" and (index == 0 or content[index - 1] != "\\"):
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(character)
    cells.append("".join(cell).strip())
    return cells


def physical_table_runs(lines):
    runs = []
    index = 0
    while index < len(lines):
        if not TABLE_LINE_RE.match(lines[index]):
            index += 1
            continue
        start = index + 1
        run = []
        while index < len(lines) and TABLE_LINE_RE.match(lines[index]):
            run.append(lines[index])
            index += 1
        runs.append((start, run))
    return runs


def expected_table(
    start, run, column_overrides, table_header_overrides, errors
):
    first = split_table_row(run[0])
    separator = run[1] if len(run) > 1 else ""
    override = table_header_overrides.get(start + 1)
    if override:
        if separator.rstrip() != override["observed"]:
            errors.append(
                f"table override at line {start + 1} expected "
                f"{override['observed']!r}, found {separator.rstrip()!r}"
            )
        separator = override["treatAs"]
    has_header = len(run) > 1 and all(
        SEPARATOR_CELL_RE.match(cell) for cell in split_table_row(separator)
    )
    if override and not has_header:
        errors.append(
            f"table override at line {start + 1} does not produce a "
            "valid header separator"
        )
    columns = (
        [column_overrides.get(value, value) for value in first]
        if has_header
        else ["" for _ in first]
    )
    data_lines = run[2:] if has_header else run
    rows = []
    for position, line in enumerate(data_lines, start=1):
        values = split_table_row(line)
        if len(values) != len(columns):
            errors.append(
                f"source table at line {start}: row {position} has "
                f"{len(values)} cells for {len(columns)} columns"
            )
        rows.append(
            {
                "position": position,
                "cells": [{"value": value} for value in values],
            }
        )
    return columns, rows


def section_for_line(sections, line_number):
    for section in sections:
        if section["lineStart"] <= line_number <= section["lineEnd"]:
            return section
    return None


def validate_subrecord(collection, record, lines, owner_end, errors):
    locator = record["sourceLocator"]
    start, end = locator["lineStart"], locator["lineEnd"]
    line = lines[start - 1]
    expected_name = None
    if collection == "actions":
        match = ACTION_RE.match(line)
        if match:
            expected_name = match.group(1)
        optional_text(record, "rulesText", line.strip(), errors)
        following = next(
            (
                (number, lines[number - 1])
                for number in range(start + 1, owner_end + 1)
                if lines[number - 1].strip()
            ),
            None,
        )
        has_example = (
            following is not None
            and following[1].startswith("*")
            and not following[1].startswith("**")
        )
        expected_end = following[0] if has_example else start
        if end != expected_end:
            errors.append(
                f"{record['slug']}: action span ends at {end}, "
                f"expected {expected_end}"
            )
        if has_example:
            optional_text(record, "examplesText", following[1].strip(), errors)
        else:
            optional_text(record, "examplesText", "", errors)
    elif collection == "claims":
        match = BOLD_LEAD_RE.match(line)
        if match:
            expected_name = match.group(1).strip().rstrip(":").strip()
        optional_text(record, "rulesText", line.strip(), errors)
        if start != end:
            errors.append(f"{record['slug']}: crew claim must be a one-line span")
    elif collection in ("trauma-conditions", "vices"):
        match = BOLD_BULLET_RE.match(line)
        if match:
            expected_name = match.group(1).strip()
        optional_text(record, "rulesText", line[2:].strip(), errors)
        if start != end:
            errors.append(f"{record['slug']}: bullet record must be a one-line span")
    elif collection == "plans":
        match = PLAN_BULLET_RE.match(line)
        if match:
            expected_name = match.group(1).strip()
            if record.get("detail") != match.group(2).strip():
                errors.append(f"{record['slug']}: detail differs from source")
        optional_text(record, "rulesText", line[2:].strip(), errors)
        if start != end:
            errors.append(f"{record['slug']}: plan must be a one-line span")
    if expected_name is None:
        errors.append(
            f"{record['slug']}: source line {start} does not match its grammar"
        )
    elif record["name"] != expected_name:
        errors.append(
            f"{record['slug']}: name {record['name']!r} != {expected_name!r}"
        )


def expected_subrecord_lines(sections, lines):
    expected = {
        "actions": set(),
        "claims": set(),
        "trauma-conditions": set(),
        "vices": set(),
        "plans": set(),
    }
    for section in sections:
        body_start = section["lineStart"] + 1
        numbered = list(enumerate(body_lines(lines, section), start=body_start))
        if (
            section["name"] == ACTIONS_HEADING
            and section["chapter"]["name"] == ACTIONS_CHAPTER
        ):
            expected["actions"].update(
                number for number, line in numbered if ACTION_RE.match(line)
            )
        if section["name"] == CREW_CLAIMS_HEADING:
            expected["claims"].update(
                number for number, line in numbered if BOLD_LEAD_RE.match(line)
            )
        if section["name"] == TRAUMA_HEADING:
            expected["trauma-conditions"].update(
                number for number, line in numbered if BOLD_BULLET_RE.match(line)
            )
        if section["name"] == VICE_HEADING:
            expected["vices"].update(
                number for number, line in numbered if BOLD_BULLET_RE.match(line)
            )
        if section["level"] == 1 and section["name"] == PLANS_CHAPTER:
            expected["plans"].update(
                number for number, line in numbered if PLAN_BULLET_RE.match(line)
            )
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    registry = load_json(root / "objects/sources/extraction-overrides.json")

    errors = []
    heading_overrides = {
        entry["line"]: entry
        for entry in registry.get("overrides", [])
        if entry.get("kind") == "heading-level"
        and entry.get("status") == "applied-in-extraction"
    }
    column_overrides = {
        entry["observed"]: entry["treatAs"]
        for entry in registry.get("overrides", [])
        if entry.get("kind") == "column-label"
        and entry.get("status") == "applied-in-extraction"
    }
    table_header_overrides = {
        entry["line"]: entry
        for entry in registry.get("overrides", [])
        if entry.get("kind") == "table-header-separator"
        and entry.get("status") == "applied-in-extraction"
    }
    sections = source_sections(lines, heading_overrides, errors)

    records = [
        (collection, load_json(path))
        for collection, path in iter_object_files(root)
    ]
    content_records = [(c, r) for c, r in records if c != "sources"]
    counts = {}
    ability_scopes = {}
    claim_types = {}
    rule_spans = {}
    rules_by_section = {}
    sub_records = []
    primary_by_start = {}

    for collection, record in content_records:
        counts[collection] = counts.get(collection, 0) + 1
        locator = record["sourceLocator"]
        owner = section_for_line(sections, locator["lineStart"])
        if owner is None:
            errors.append(
                f"{record['slug']}: locator start {locator['lineStart']} "
                "is outside every physical section"
            )
            continue
        for field, expected in (
            ("chapter", owner["chapter"]["name"]),
            ("section", owner["section"]),
            ("heading", owner["name"]),
        ):
            if locator.get(field) != expected:
                errors.append(
                    f"{record['slug']}: locator {field} "
                    f"{locator.get(field)!r} != {expected!r}"
                )
        if locator["lineEnd"] > owner["lineEnd"]:
            errors.append(f"{record['slug']}: locator escapes its physical section")

        is_prison_claim = (
            collection == "claims" and record.get("claimType") == "prison"
        )
        is_primary = collection in {
            "rules",
            "special-abilities",
            "entanglements",
            "downtime-activities",
            "teamwork-maneuvers",
        } or is_prison_claim
        if is_primary:
            primary_by_start.setdefault(locator["lineStart"], []).append(
                (collection, record)
            )
            if (
                locator["lineStart"] != owner["lineStart"]
                or locator["lineEnd"] != owner["lineEnd"]
            ):
                errors.append(f"{record['slug']}: section span is not exact")
            expected = expected_collection(owner)
            if collection != expected:
                errors.append(
                    f"{record['slug']}: section grammar expects {expected}, "
                    f"found {collection}"
                )
            if record["name"] != owner["name"]:
                errors.append(f"{record['slug']}: printed heading name differs")
            if collection == "rules":
                optional_text(
                    record,
                    "rulesText",
                    expected_rule_text(lines, owner),
                    errors,
                )
                rule_spans[owner["section"]] = (
                    locator["lineStart"],
                    locator["lineEnd"],
                    record["@id"],
                )
                rules_by_section[owner["section"]] = record
            else:
                prose, commentary = expected_catalog_text(lines, owner)
                optional_text(record, "rulesText", prose, errors)
                optional_text(record, "commentary", commentary, errors)

        if collection == "actions":
            if "attribute" not in record:
                errors.append(f"{record['slug']}: action missing attribute")
            sub_records.append((collection, record))
        if collection == "special-abilities":
            expected_scope = (
                "character"
                if owner["parent"]["name"] == CHARACTER_ABILITIES_HEADING
                else "crew"
            )
            if record.get("abilityScope") != expected_scope:
                errors.append(f"{record['slug']}: incorrect abilityScope")
            scope = record.get("abilityScope", "")
            ability_scopes[scope] = ability_scopes.get(scope, 0) + 1
        if collection == "claims":
            claim_type = record.get("claimType", "")
            claim_types[claim_type] = claim_types.get(claim_type, 0) + 1
            if claim_type == "crew":
                sub_records.append((collection, record))
        if collection in ("trauma-conditions", "vices", "plans"):
            sub_records.append((collection, record))

    for section in sections:
        primary = primary_by_start.get(section["lineStart"], [])
        if len(primary) != 1:
            errors.append(
                f"source section {section['section']} {section['name']!r}: "
                f"expected one primary record, found {len(primary)}"
            )

    expected_subspans = expected_subrecord_lines(sections, lines)
    actual_subspans = {collection: set() for collection in expected_subspans}
    rule_ids = {section: data[2] for section, data in rule_spans.items()}
    for collection, record in sub_records:
        locator = record["sourceLocator"]
        actual_subspans[collection].add(locator["lineStart"])
        owner = rule_spans.get(locator["section"])
        if owner is None:
            errors.append(f"{record['slug']}: no owning rule for §{locator['section']}")
        elif not (
            owner[0]
            <= locator["lineStart"]
            <= locator["lineEnd"]
            <= owner[1]
        ):
            errors.append(f"{record['slug']}: span escapes owning rule")
        if record.get("partOf", {}).get("@id") != rule_ids.get(locator["section"]):
            errors.append(f"{record['slug']}: partOf does not reference owning rule")
        physical_owner = section_for_line(sections, locator["lineStart"])
        owner_end = (
            physical_owner["lineEnd"]
            if physical_owner is not None
            else locator["lineEnd"]
        )
        validate_subrecord(collection, record, lines, owner_end, errors)
    for collection, expected in expected_subspans.items():
        if actual_subspans[collection] != expected:
            errors.append(
                f"{collection}: typed source lines {sorted(actual_subspans[collection])} "
                f"!= grammar hits {sorted(expected)}"
            )

    table_records = {
        record["sourceLocator"]["lineStart"]: record
        for collection, record in content_records
        if collection == "tables"
    }
    physical_starts = set()
    table_ids_by_section = {}
    action_attributes = {}
    for start, run in physical_table_runs(lines):
        physical_starts.add(start)
        record = table_records.get(start)
        if record is None:
            errors.append(f"source table at line {start}: missing Table record")
            continue
        expected_raw = "\n".join(run)
        if record.get("rawText") != expected_raw:
            errors.append(f"{record['slug']}: rawText differs from source span")
        if record["sourceLocator"]["lineEnd"] != start + len(run) - 1:
            errors.append(f"{record['slug']}: table span is not exact")
        owner = section_for_line(sections, start)
        if owner and record.get("name") != owner["name"]:
            errors.append(f"{record['slug']}: table name differs from owning heading")
        if owner:
            table_ids_by_section.setdefault(owner["section"], []).append(
                {"@id": record["@id"]}
            )
        columns, rows = expected_table(
            start, run, column_overrides, table_header_overrides, errors
        )
        if record.get("columns") != columns:
            errors.append(f"{record['slug']}: columns differ from source table")
        if record.get("rows") != rows:
            errors.append(f"{record['slug']}: rows differ from source table")
        for row in record.get("rows", []):
            if len(row.get("cells", [])) != len(record.get("columns", [])):
                errors.append(
                    f"{record['slug']}: row {row.get('position')} width differs "
                    "from columns"
                )
        heading = record["sourceLocator"]["heading"]
        if heading in ATTRIBUTES:
            for row in rows:
                match = BOLD_LEAD_RE.match(row["cells"][-1]["value"])
                if match:
                    action_attributes[match.group(1).strip()] = heading
    extra_tables = set(table_records) - physical_starts
    if extra_tables:
        errors.append(f"table records without physical runs: {sorted(extra_tables)}")

    for section, rule in rules_by_section.items():
        expected = table_ids_by_section.get(section, [])
        actual = rule.get("relatedTables", [])
        if actual != expected:
            errors.append(
                f"{rule['slug']}: relatedTables {actual!r} != {expected!r}"
            )

    for collection, record in sub_records:
        if collection == "actions":
            expected = action_attributes.get(record["name"])
            if record.get("attribute") != expected:
                errors.append(
                    f"{record['slug']}: attribute {record.get('attribute')!r} "
                    f"!= table-backed {expected!r}"
                )

    for collection, expected in EXPECTED_COUNTS.items():
        if counts.get(collection, 0) != expected:
            errors.append(
                f"{collection}: expected {expected} records, "
                f"found {counts.get(collection, 0)}"
            )
    if ability_scopes != EXPECTED_ABILITIES:
        errors.append(
            f"special-abilities: scope counts {ability_scopes} "
            f"!= {EXPECTED_ABILITIES}"
        )
    if claim_types != EXPECTED_CLAIMS:
        errors.append(f"claims: type counts {claim_types} != {EXPECTED_CLAIMS}")

    source_records = [
        record for collection, record in records if collection == "sources"
    ]
    if len(source_records) != 1:
        errors.append(f"expected one source record, found {len(source_records)}")
    else:
        source = source_records[0]
        if source.get("attributionStatement") != ATTRIBUTION_STATEMENT:
            errors.append("source record attribution statement differs")
        if source.get("conversionStatement") != CONVERSION_STATEMENT:
            errors.append("source record conversion statement differs")
        if source.get("license") != "CC-BY-3.0":
            errors.append("source record license is not CC-BY-3.0")
        if source.get("licenseUrl", {}).get("@id") != (
            "https://creativecommons.org/licenses/by/3.0/"
        ):
            errors.append("source record licenseUrl differs")
    manifest = load_json(root / "objects" / MANIFEST_NAME)
    metadata = manifest.get("metadata", {})
    if metadata.get("attributionStatement") != ATTRIBUTION_STATEMENT:
        errors.append("manifest attribution statement differs")
    if metadata.get("conversionStatement") != CONVERSION_STATEMENT:
        errors.append("manifest conversion statement differs")
    llms_full = (root / "llms-full.txt").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for label, text in (("llms-full.txt", llms_full), ("README.md", readme)):
        if ATTRIBUTION_STATEMENT not in text:
            errors.append(f"{label} missing the attribution statement")
        if CONVERSION_STATEMENT not in text:
            errors.append(f"{label} missing the conversion statement")

    if errors:
        print("\n".join(errors[:80]))
        print(f"FAIL: {len(errors)} fidelity errors")
        sys.exit(1)
    print(
        f"fidelity: {len(sections)} source sections and "
        f"{sum(counts.values())} records exactly match source prose, tables, "
        "typed grammar hits, locators, classifications, and rights metadata"
    )


if __name__ == "__main__":
    main()
