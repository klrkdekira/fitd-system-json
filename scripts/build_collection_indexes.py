"""Generate objects/collection-index.json: display metadata for the explorer.

One compact entry per record (slug, name, sub-line, group) so index.html can
render grouped, contextual lists without fetching every record.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fitdlib import ATTRIBUTES, COLLECTIONS, dump_json, iter_object_files, load_json


def chapter_order(locator):
    return (
        int(locator.get("section", "99.0").split(".")[0]),
        locator.get("lineStart", 0),
    )


def entry_for(collection: str, record: dict):
    name = record["name"]
    slug = record["slug"]
    locator = record.get("sourceLocator", {})
    if collection == "actions":
        attribute = record.get("attribute", "")
        group = attribute
        sub = record.get("rulesText", "")[:80]
        order = (
            ATTRIBUTES.index(attribute) if attribute in ATTRIBUTES else 9,
            name.lower(),
        )
    elif collection == "special-abilities":
        scope = record.get("abilityScope", "")
        group = "Crew Abilities" if scope == "crew" else "Character Abilities"
        sub = scope
        order = (scope, locator.get("lineStart", 0))
    elif collection == "entanglements":
        group = "Entanglements"
        sub = record.get("rulesText", "")[:80]
        order = (0, locator.get("lineStart", 0))
    elif collection == "downtime-activities":
        group = "Downtime Activities"
        sub = record.get("rulesText", "")[:80]
        order = (0, locator.get("lineStart", 0))
    elif collection == "claims":
        claim_type = record.get("claimType", "")
        group = "Prison Claims" if claim_type == "prison" else "Crew Claims"
        sub = f"{claim_type} claim"
        order = (claim_type, locator.get("lineStart", 0))
    elif collection == "trauma-conditions":
        group = "Trauma Conditions"
        sub = record.get("rulesText", "")[:80]
        order = (0, locator.get("lineStart", 0))
    elif collection == "vices":
        group = "Vices"
        sub = record.get("rulesText", "")[:80]
        order = (0, locator.get("lineStart", 0))
    elif collection == "plans":
        group = "Plans"
        sub = record.get("detail", "")
        order = (0, locator.get("lineStart", 0))
    elif collection == "teamwork-maneuvers":
        group = "Teamwork Maneuvers"
        sub = record.get("rulesText", "")[:80]
        order = (0, locator.get("lineStart", 0))
    elif collection in ("rules", "tables"):
        group = locator.get("chapter", "")
        sub = f"§{locator.get('section', '')}"
        order = chapter_order(locator)
    else:  # sources
        group = "Sources"
        sub = record.get("license", "")
        order = (0, name.lower())
    return order, {"slug": slug, "name": name, "sub": sub.strip(" ·"), "group": group}


def build(root: Path) -> None:
    index = {}
    for collection in COLLECTIONS:
        entries = []
        for c, path in iter_object_files(root):
            if c != collection:
                continue
            entries.append(entry_for(collection, load_json(path)))
        entries.sort(key=lambda pair: pair[0])
        index[collection] = [entry for _, entry in entries]
    dump_json(root / "objects" / "collection-index.json", {"collections": index})
    total = sum(len(v) for v in index.values())
    print(f"collection-index: {total} entries")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
