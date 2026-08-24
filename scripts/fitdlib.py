"""Shared constants and helpers for the Blades in the Dark SRD corpus pipeline.

Everything under objects/ is generated from Blades-in-the-Dark-SRD.md by
scripts in this directory. Determinism rules: no timestamps, no randomness,
sorted listings, fixed JSON formatting.

The architecture follows the replication approach established by graph20
(https://cheeleong.dev/graph20/).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterator

BASE = "https://cheeleong.dev/fitd-system-json/"
CONTEXT_IRI = BASE + "systems/context.jsonld"
SOURCE_ID = BASE + "objects/sources/blades-in-the-dark-srd"
SOURCE_FILE = "Blades-in-the-Dark-SRD.md"
SYSTEM_SLUG = "fitd"
VERSION = "0.2.0"
MANIFEST_NAME = f"{SYSTEM_SLUG}-system-data.jsonld"
BUNDLE_NAME = f"{SYSTEM_SLUG}-system-data.bundle.jsonld"

# Required CC-BY-3.0 attribution, exactly as published at
# https://bladesinthedark.com/licensing.
ATTRIBUTION_STATEMENT = (
    "This work is based on Blades in the Dark (found at "
    "http://www.bladesinthedark.com/), product of One Seven Design, developed "
    "and authored by John Harper, and licensed for our use under the Creative "
    "Commons Attribution 3.0 Unported license "
    "(http://creativecommons.org/licenses/by/3.0/)."
)

# Provenance of the Markdown conversion this corpus is extracted from.
CONVERSION_STATEMENT = (
    "The in-scope source file is the Markdown conversion of the Blades in the "
    "Dark SRD text published by Randy Oest (amazingrando) at "
    "https://github.com/amazingrando/blades-in-the-dark-srd-content, file "
    "Blades-in-the-Dark-SRD.md at commit "
    "ac2747ffc0806b2be9f14d29b2ace5dca6149bc3 (2022-04-08), retrieved on "
    "2026-08-24."
)
SOURCE_VERSION = (
    "amazingrando/blades-in-the-dark-srd-content@ac2747ff (2022-04-08)"
)
SOURCE_REPOSITORY = "https://github.com/amazingrando/blades-in-the-dark-srd-content"

COLLECTIONS = [
    "sources",
    "rules",
    "tables",
    "actions",
    "special-abilities",
    "entanglements",
    "downtime-activities",
    "claims",
    "trauma-conditions",
    "vices",
    "plans",
    "teamwork-maneuvers",
]

COLLECTION_TYPES = {
    "sources": "Source",
    "rules": "Rule",
    "tables": "Table",
    "actions": "Action",
    "special-abilities": "SpecialAbility",
    "entanglements": "Entanglement",
    "downtime-activities": "DowntimeActivity",
    "claims": "Claim",
    "trauma-conditions": "TraumaCondition",
    "vices": "Vice",
    "plans": "Plan",
    "teamwork-maneuvers": "TeamworkManeuver",
}

SCHEMA_FOR_COLLECTION = {
    "sources": "source.schema.json",
    "rules": "rule.schema.json",
    "tables": "table.schema.json",
    "actions": "action.schema.json",
    "special-abilities": "special-ability.schema.json",
    "entanglements": "entanglement.schema.json",
    "downtime-activities": "downtime-activity.schema.json",
    "claims": "claim.schema.json",
    "trauma-conditions": "trauma-condition.schema.json",
    "vices": "vice.schema.json",
    "plans": "plan.schema.json",
    "teamwork-maneuvers": "teamwork-maneuver.schema.json",
}

# The three attributes as printed in the source; the action-to-attribute
# mapping itself is read from the EXAMPLE ACTION & ATTRIBUTE RATINGS tables,
# never hardcoded.
ATTRIBUTES = ["Insight", "Prowess", "Resolve"]

# Headings that gate catalog extraction. Values are exact printed headings.
ACTIONS_HEADING = "Actions"
ACTIONS_CHAPTER = "Actions & Attributes"
RATINGS_HEADING = "EXAMPLE ACTION & ATTRIBUTE RATINGS"
CHARACTER_ABILITIES_HEADING = "Special abilities"
CREW_ABILITIES_HEADING = "Crew special abilities"
ENTANGLEMENTS_CHAPTER = "Entanglements"
DOWNTIME_CHAPTER = "Downtime activities"
PRISON_CLAIMS_HEADING = "Prison claims"
CREW_CLAIMS_HEADING = "Make a Claim Map for the Crew"
TRAUMA_HEADING = "Trauma Conditions"
VICE_HEADING = "Choose your vice"
PLANS_CHAPTER = "Planning & engagement"
TEAMWORK_HEADING = "Teamwork"

# The six downtime activities as listed in the chapter's own bullet list.
DOWNTIME_ACTIVITY_NAMES = [
    "Acquire asset",
    "Long-term project",
    "Recover",
    "Reduce heat",
    "Train",
    "Indulge vice",
]

# Level-3 sections under "Prison claims" that are reference cards rather
# than claims (see SPECIFICATION.md).
PRISON_CLAIM_EXCLUDE = {"CLAIMS: PRISON"}


def slugify(text: str) -> str:
    text = text.lower().replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unnamed"


def clean_heading(text: str) -> str:
    """Strip Markdown emphasis markers from a printed heading."""
    return re.sub(r"\*+", "", text).strip()


def sha256_of(path: Path) -> str:
    return "sha256-" + hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_object_files(root: Path):
    objects = root / "objects"
    for collection in COLLECTIONS:
        directory = objects / collection
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.jsonld")):
            yield collection, path


# Fields that identify or locate a value but are not useful corpus text.
PROJECTION_IGNORED_KEYS = {
    "@context",
    "@id",
    "@type",
    "slug",
    "source",
    "sourceLocator",
    "contentDigest",
    "sourceDigest",
    "corpusDigest",
}


def iter_text_fragments(
    value,
    path: str = "",
    locator: dict | None = None,
) -> Iterator[dict]:
    """Yield every human-meaningful scalar with its structural path.

    This is the shared, recursive textual projection used by LLM output and
    full-text search. A nested source locator overrides its parent's locator
    so nested fragments retain precise provenance.
    """
    if isinstance(value, dict):
        inherited = value.get("sourceLocator", locator)
        for key, child in value.items():
            if key in PROJECTION_IGNORED_KEYS:
                continue
            child_path = f"{path}.{key}" if path else key
            yield from iter_text_fragments(child, child_path, inherited)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_text_fragments(child, f"{path}[{index}]", locator)
    elif isinstance(value, (str, int, float, bool)):
        text = str(value)
        if text:
            yield {"path": path, "text": text, "sourceLocator": locator}


def projected_text(record: dict) -> str:
    """Return a complete plain-text projection of a corpus record."""
    return "\n".join(fragment["text"] for fragment in iter_text_fragments(record))
