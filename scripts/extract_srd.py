"""Extract modular JSON-LD records from Blades-in-the-Dark-SRD.md.

Segmentation model:

- Every Markdown heading (any level) starts a section. A section spans its
  heading line through the line before the next heading, with trailing blank
  lines trimmed. Level-1 headings are chapters; sections are numbered
  ``<chapter>.<ordinal>`` in document order, chapter headings included.
- Sections claimed by a catalog grammar (special abilities, entanglements,
  downtime activities, prison claims, teamwork maneuvers) become typed
  records instead of rules.
- Paragraph- and bullet-grained entities (actions, crew claims, trauma
  conditions, vices, plans) are typed indexes over rule prose: the owning
  rule keeps the source-faithful text and the typed records carry sub-spans
  plus a partOf link to the owning rule.
- Pipe-table runs become Table records with raw source text; the owning
  section's rule links them via relatedTables and its rulesText excludes the
  physical table lines.

Registered source normalizations are applied only through
objects/sources/extraction-overrides.json; the extractor verifies the
observed text before honouring an override and never repairs the source
silently.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from fitdlib import (
    ACTIONS_CHAPTER,
    ACTIONS_HEADING,
    ATTRIBUTES,
    ATTRIBUTION_STATEMENT,
    BASE,
    CHARACTER_ABILITIES_HEADING,
    COLLECTIONS,
    CONTEXT_IRI,
    CONVERSION_STATEMENT,
    CREW_ABILITIES_HEADING,
    CREW_CLAIMS_HEADING,
    DOWNTIME_ACTIVITY_NAMES,
    DOWNTIME_CHAPTER,
    ENTANGLEMENTS_CHAPTER,
    PLANS_CHAPTER,
    PRISON_CLAIMS_HEADING,
    PRISON_CLAIM_EXCLUDE,
    RATINGS_HEADING,
    SOURCE_FILE,
    SOURCE_ID,
    SOURCE_REPOSITORY,
    SOURCE_VERSION,
    TEAMWORK_HEADING,
    TRAUMA_HEADING,
    VICE_HEADING,
    clean_heading,
    dump_json,
    load_json,
    sha256_of,
    slugify,
)

HEADING_RE = re.compile(r"^(#{1,6}) (.+?)\s*$")
TABLE_LINE_RE = re.compile(r"^\|.*\|\s*$")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
ACTION_RE = re.compile(r"^When you \*\*(\w+)\*\*, .*")
BOLD_LEAD_RE = re.compile(r"^\*\*([^*]+?)\*\*")
BOLD_BULLET_RE = re.compile(r"^\* \*\*([^*]+?)\*\*: .*")
PLAN_BULLET_RE = re.compile(r"^\* (\w+) - .+ \*Detail: (.+)\*$")


class Section:
    def __init__(self, level, title, line_start):
        self.level = level
        self.title = title  # printed heading text
        self.name = clean_heading(title)
        self.line_start = line_start  # 1-based heading line
        self.line_end = line_start
        self.body_start = line_start + 1
        self.chapter = None  # chapter Section
        self.parent = None  # nearest enclosing Section
        self.section_number = None  # "<chapter>.<ordinal>"
        self.body_lines = []  # [(1-based line, text)]

    @property
    def body(self):
        return "\n".join(text for _, text in self.body_lines)


def parse_sections(lines, heading_overrides):
    """Split the source into flat sections with parent/chapter links."""
    sections = []
    stack = []
    for index, raw in enumerate(lines, start=1):
        match = HEADING_RE.match(raw)
        level = None
        title = None
        if match:
            level, title = len(match.group(1)), match.group(2)
        override = heading_overrides.get(index)
        if override:
            observed = override["observed"]
            if raw.rstrip() != observed:
                raise SystemExit(
                    f"extraction override at line {index} expected "
                    f"{observed!r}, found {raw.rstrip()!r}"
                )
            treat_match = HEADING_RE.match(override["treatAs"])
            level, title = len(treat_match.group(1)), treat_match.group(2)
        if level is None:
            if sections:
                sections[-1].body_lines.append((index, raw))
            continue
        section = Section(level, title, index)
        while stack and stack[-1].level >= level:
            stack.pop()
        section.parent = stack[-1] if stack else None
        section.chapter = section if level == 1 else (
            stack[0] if stack else None
        )
        stack.append(section)
        sections.append(section)

    # Close spans (trailing blank lines trimmed) and number sections.
    chapter_ordinal = 0
    within = 0
    for position, section in enumerate(sections):
        last = (
            sections[position + 1].line_start - 1
            if position + 1 < len(sections)
            else len(lines)
        )
        while last > section.line_start and not lines[last - 1].strip():
            last -= 1
        section.line_end = last
        section.body_lines = [
            (line, text)
            for line, text in section.body_lines
            if line <= last
        ]
        if section.level == 1:
            chapter_ordinal += 1
            within = 0
        within += 1
        section.chapter_ordinal = chapter_ordinal
        section.section_number = f"{chapter_ordinal}.{within}"
    return sections


def parse_table_runs(section):
    """Yield (start_line, [raw table lines]) for each pipe run in a section."""
    run = []
    start = None
    for line_number, text in section.body_lines + [(None, "")]:
        if line_number is not None and TABLE_LINE_RE.match(text):
            if not run:
                start = line_number
            run.append(text)
        elif run:
            yield start, run
            run, start = [], None


def split_row(line):
    """Split a Markdown table row without breaking escaped pipe content."""
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


def parse_table(table_lines, separator_override=None):
    """Return (columns, rows) for a GFM pipe table."""
    first = split_row(table_lines[0])
    separator_line = separator_override or (
        table_lines[1] if len(table_lines) > 1 else ""
    )
    has_header = len(table_lines) > 1 and all(
        SEPARATOR_CELL_RE.match(cell) for cell in split_row(separator_line)
    )
    columns = first if has_header else ["" for _ in first]
    data_lines = table_lines[2:] if has_header else table_lines
    rows = []
    for line in data_lines:
        cells = split_row(line)
        rows.append(
            {
                "position": len(rows) + 1,
                "cells": [{"value": value} for value in cells],
            }
        )
    return columns, rows


class Emitter:
    def __init__(self, root: Path):
        self.root = root
        self.records = {name: [] for name in COLLECTIONS}
        self.slugs = {name: set() for name in COLLECTIONS}

    def unique_slug(self, collection, base):
        slug = base
        counter = 2
        while slug in self.slugs[collection]:
            slug = f"{base}-{counter}"
            counter += 1
        self.slugs[collection].add(slug)
        return slug

    def rule_id(self, section):
        """Canonical @id of the Rule record a section becomes."""
        slug = (
            f"{section.section_number.replace('.', '-')}-{slugify(section.name)}"
        )
        return f"{BASE}objects/rules/{slug}"

    def locator(self, section, line_start=None, line_end=None):
        return {
            "chapter": section.chapter.name,
            "section": section.section_number,
            "heading": section.name,
            "lineStart": line_start or section.line_start,
            "lineEnd": line_end or section.line_end,
        }

    def new_record(self, collection, type_name, name, slug_base, locator):
        slug = self.unique_slug(collection, slug_base)
        record = {
            "@context": CONTEXT_IRI,
            "@id": f"{BASE}objects/{collection}/{slug}",
            "@type": type_name,
            "name": name,
            "slug": slug,
            "source": {"@id": SOURCE_ID},
            "sourceLocator": locator,
        }
        self.records[collection].append(record)
        return record

    def write(self):
        objects = self.root / "objects"
        for collection in COLLECTIONS:
            directory = objects / collection
            if directory.is_dir():
                for stale in directory.glob("*.jsonld"):
                    stale.unlink()
            directory.mkdir(parents=True, exist_ok=True)
            for record in self.records[collection]:
                dump_json(directory / f"{record['slug']}.jsonld", record)


def normalize_column(value, column_overrides):
    """Apply registered header-cell normalizations (e.g. '[]()' -> '')."""
    return column_overrides.get(value, value)


def prose_without_tables(section, table_spans):
    """Section body minus physical table lines and '---' separators."""
    kept = []
    for line_number, text in section.body_lines:
        if any(start <= line_number <= end for start, end in table_spans):
            continue
        if text.strip() == "---":
            continue
        kept.append(text)
    return "\n".join(kept).strip("\n").strip()


def split_commentary(body_lines):
    """Split a catalog section body into rules prose and '>' commentary."""
    prose = []
    commentary = []
    for _, text in body_lines:
        if text.startswith(">"):
            commentary.append(text[1:].lstrip() if len(text) > 1 else "")
        elif text.strip() == "---":
            continue
        else:
            prose.append(text)
    rules_text = "\n".join(prose).strip("\n").strip()
    commentary_text = "\n".join(commentary).strip("\n").strip()
    return rules_text, commentary_text


def action_attribute_map(sections, lines):
    """Read the action-to-attribute mapping from the printed rating tables."""
    mapping = {}
    ratings = [s for s in sections if s.name == RATINGS_HEADING]
    if len(ratings) != 1:
        raise SystemExit("expected one EXAMPLE ACTION & ATTRIBUTE RATINGS section")
    for section in sections:
        if section.parent is not ratings[0] or section.name not in ATTRIBUTES:
            continue
        for _, run in parse_table_runs(section):
            _, rows = parse_table(run)
            for row in rows:
                last = row["cells"][-1]["value"]
                match = BOLD_LEAD_RE.match(last)
                if match:
                    mapping[match.group(1).strip()] = section.name
    return mapping


def extract_actions(emitter, sections, lines, attribute_map):
    count = 0
    holders = [
        s
        for s in sections
        if s.name == ACTIONS_HEADING and s.chapter.name == ACTIONS_CHAPTER
    ]
    if len(holders) != 1:
        raise SystemExit("expected one Actions section in Actions & Attributes")
    holder = holders[0]
    body = holder.body_lines
    for index, (line_number, text) in enumerate(body):
        match = ACTION_RE.match(text)
        if not match:
            continue
        name = match.group(1)
        line_end = line_number
        examples = None
        for later_line, later_text in body[index + 1:]:
            if not later_text.strip():
                continue
            if later_text.startswith("*") and not later_text.startswith("**"):
                examples = later_text.strip()
                line_end = later_line
            break
        if name not in attribute_map:
            raise SystemExit(f"action {name!r} missing from the rating tables")
        record = emitter.new_record(
            "actions",
            "Action",
            name,
            slugify(name),
            emitter.locator(holder, line_start=line_number, line_end=line_end),
        )
        record["attribute"] = attribute_map[name]
        record["partOf"] = {"@id": emitter.rule_id(holder)}
        record["rulesText"] = text.strip()
        if examples:
            record["examplesText"] = examples
        count += 1
    return count


def extract_catalog_sections(emitter, sections):
    """Sections that become typed records instead of rules."""
    claimed = set()

    def emit(section, collection, type_name, extra):
        rules_text, commentary = split_commentary(section.body_lines)
        record = emitter.new_record(
            collection,
            type_name,
            section.name,
            slugify(section.name),
            emitter.locator(section),
        )
        if rules_text:
            record["rulesText"] = rules_text
        if commentary:
            record["commentary"] = commentary
        record.update(extra)
        claimed.add(section)

    downtime_names = {name.lower() for name in DOWNTIME_ACTIVITY_NAMES}
    for section in sections:
        parent = section.parent
        if parent is not None and parent.name == CHARACTER_ABILITIES_HEADING:
            emit(section, "special-abilities", "SpecialAbility",
                 {"abilityScope": "character"})
        elif parent is not None and parent.name == CREW_ABILITIES_HEADING:
            emit(section, "special-abilities", "SpecialAbility",
                 {"abilityScope": "crew"})
        elif (
            section.level == 3
            and parent is not None
            and parent.level == 1
            and parent.name == ENTANGLEMENTS_CHAPTER
        ):
            emit(section, "entanglements", "Entanglement", {})
        elif (
            section.level == 3
            and parent is not None
            and parent.level == 1
            and parent.name == DOWNTIME_CHAPTER
            and section.name.lower() in downtime_names
        ):
            emit(section, "downtime-activities", "DowntimeActivity", {})
        elif (
            section.level == 3
            and parent is not None
            and parent.name == PRISON_CLAIMS_HEADING
            and section.name not in PRISON_CLAIM_EXCLUDE
        ):
            emit(section, "claims", "Claim", {"claimType": "prison"})
        elif (
            section.level == 3
            and parent is not None
            and parent.level == 2
            and parent.name == TEAMWORK_HEADING
        ):
            emit(section, "teamwork-maneuvers", "TeamworkManeuver", {})
    return claimed


def extract_crew_claims(emitter, sections):
    holders = [s for s in sections if s.name == CREW_CLAIMS_HEADING]
    if len(holders) != 1:
        raise SystemExit("expected one crew claim map section")
    holder = holders[0]
    count = 0
    for line_number, text in holder.body_lines:
        match = BOLD_LEAD_RE.match(text)
        if not match:
            continue
        name = match.group(1).strip().rstrip(":").strip()
        record = emitter.new_record(
            "claims",
            "Claim",
            name,
            slugify(name),
            emitter.locator(holder, line_start=line_number, line_end=line_number),
        )
        record["claimType"] = "crew"
        record["partOf"] = {"@id": emitter.rule_id(holder)}
        record["rulesText"] = text.strip()
        count += 1
    return count


def extract_bold_bullets(emitter, sections, heading, collection, type_name):
    """Bold-led ':' bullets in one section become sub-span records."""
    holders = [s for s in sections if s.name == heading]
    if len(holders) != 1:
        raise SystemExit(f"expected one {heading} section")
    holder = holders[0]
    count = 0
    for line_number, text in holder.body_lines:
        match = BOLD_BULLET_RE.match(text)
        if not match:
            continue
        record = emitter.new_record(
            collection,
            type_name,
            match.group(1).strip(),
            slugify(match.group(1)),
            emitter.locator(holder, line_start=line_number, line_end=line_number),
        )
        record["partOf"] = {"@id": emitter.rule_id(holder)}
        record["rulesText"] = text[2:].strip()
        count += 1
    return count


def extract_plans(emitter, sections):
    holders = [
        s for s in sections if s.level == 1 and s.name == PLANS_CHAPTER
    ]
    if len(holders) != 1:
        raise SystemExit("expected one Planning & engagement chapter")
    holder = holders[0]
    count = 0
    for line_number, text in holder.body_lines:
        match = PLAN_BULLET_RE.match(text)
        if not match:
            continue
        record = emitter.new_record(
            "plans",
            "Plan",
            match.group(1).strip(),
            slugify(match.group(1)),
            emitter.locator(holder, line_start=line_number, line_end=line_number),
        )
        record["partOf"] = {"@id": emitter.rule_id(holder)}
        record["rulesText"] = text[2:].strip()
        record["detail"] = match.group(2).strip()
        count += 1
    return count


def extract_tables(
    emitter, sections, column_overrides, table_header_overrides
):
    total = 0
    tables_by_section = {}
    unused_header_overrides = set(table_header_overrides)
    for section in sections:
        for start, run in parse_table_runs(section):
            override = table_header_overrides.get(start + 1)
            separator_override = None
            if override:
                unused_header_overrides.discard(start + 1)
                if len(run) < 2 or run[1].rstrip() != override["observed"]:
                    found = run[1].rstrip() if len(run) > 1 else None
                    raise SystemExit(
                        f"extraction override at line {start + 1} expected "
                        f"{override['observed']!r}, found {found!r}"
                    )
                separator_override = override["treatAs"]
                if not all(
                    SEPARATOR_CELL_RE.match(cell)
                    for cell in split_row(separator_override)
                ):
                    raise SystemExit(
                        f"extraction override at line {start + 1} does not "
                        "produce a valid table header separator"
                    )
            columns, rows = parse_table(run, separator_override)
            record = emitter.new_record(
                "tables",
                "Table",
                section.name,
                f"{section.section_number.replace('.', '-')}-{slugify(section.name)}",
                emitter.locator(
                    section, line_start=start, line_end=start + len(run) - 1
                ),
            )
            record["columns"] = [
                normalize_column(value, column_overrides) for value in columns
            ]
            record["rows"] = rows
            record["rawText"] = "\n".join(run)
            tables_by_section.setdefault(section, []).append(
                (record, start, start + len(run) - 1)
            )
            total += 1
    if unused_header_overrides:
        raise SystemExit(
            "table header overrides do not target table separators: "
            f"{sorted(unused_header_overrides)}"
        )
    return total, tables_by_section


def extract_rules(emitter, sections, claimed, tables_by_section):
    count = 0
    for section in sections:
        if section in claimed:
            continue
        tables = tables_by_section.get(section, [])
        record = emitter.new_record(
            "rules",
            "Rule",
            section.name,
            f"{section.section_number.replace('.', '-')}-{slugify(section.name)}",
            emitter.locator(section),
        )
        record["section"] = section.section_number
        rules_text = prose_without_tables(
            section, [(start, end) for _, start, end in tables]
        )
        if rules_text:
            record["rulesText"] = rules_text
        if tables:
            record["relatedTables"] = [
                {"@id": table["@id"]} for table, _, _ in tables
            ]
        count += 1
    return count


def emit_source_record(emitter, root):
    record = {
        "@context": CONTEXT_IRI,
        "@id": SOURCE_ID,
        "@type": "Source",
        "name": "Blades in the Dark SRD",
        "slug": "blades-in-the-dark-srd",
        "author": "John Harper",
        "publisher": "One Seven Design",
        "sourceVersion": SOURCE_VERSION,
        "license": "CC-BY-3.0",
        "licenseUrl": {"@id": "https://creativecommons.org/licenses/by/3.0/"},
        "attributionStatement": ATTRIBUTION_STATEMENT,
        "conversionStatement": CONVERSION_STATEMENT,
        "canonicalUrl": {"@id": "https://bladesinthedark.com/"},
        "retrievedFrom": {"@id": SOURCE_REPOSITORY},
        "sourceFile": SOURCE_FILE,
        "contentDigest": sha256_of(root / SOURCE_FILE),
    }
    emitter.records["sources"].append(record)


def run_extraction(root: Path):
    lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
    overrides = load_json(root / "objects/sources/extraction-overrides.json")
    heading_overrides = {
        entry["line"]: entry
        for entry in overrides.get("overrides", [])
        if entry.get("kind") == "heading-level"
        and entry.get("status") == "applied-in-extraction"
    }
    column_overrides = {}
    table_header_overrides = {}
    for entry in overrides.get("overrides", []):
        if (
            entry.get("kind") == "column-label"
            and entry.get("status") == "applied-in-extraction"
        ):
            column_overrides[entry["observed"]] = entry["treatAs"]
        if (
            entry.get("kind") == "table-header-separator"
            and entry.get("status") == "applied-in-extraction"
        ):
            table_header_overrides[entry["line"]] = entry

    sections = parse_sections(lines, heading_overrides)
    emitter = Emitter(root)
    emit_source_record(emitter, root)

    attribute_map = action_attribute_map(sections, lines)
    action_count = extract_actions(emitter, sections, lines, attribute_map)
    claimed = extract_catalog_sections(emitter, sections)
    crew_claims = extract_crew_claims(emitter, sections)
    trauma = extract_bold_bullets(
        emitter, sections, TRAUMA_HEADING, "trauma-conditions", "TraumaCondition"
    )
    vices = extract_bold_bullets(
        emitter, sections, VICE_HEADING, "vices", "Vice"
    )
    plans = extract_plans(emitter, sections)
    table_count, tables_by_section = extract_tables(
        emitter, sections, column_overrides, table_header_overrides
    )
    rule_count = extract_rules(emitter, sections, claimed, tables_by_section)

    emitter.write()
    counts = {name: len(emitter.records[name]) for name in COLLECTIONS}
    total = sum(counts.values())
    print(
        f"extracted {total} records: "
        + ", ".join(f"{name}={counts[name]}" for name in COLLECTIONS)
    )
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    run_extraction(Path(args.root).resolve())


if __name__ == "__main__":
    main()
