"""Line-level source coverage ledger.

Maps every non-blank source line to the records whose sourceLocator spans
consume it, and fails when any line is uncovered. The Blades SRD Markdown
begins at its first chapter heading, so the whole file is content. Writes
objects/sources/source-coverage.json.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fitdlib import SOURCE_FILE, dump_json, iter_object_files, load_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    lines = (root / SOURCE_FILE).read_text(encoding="utf-8").splitlines()

    covered = [0] * (len(lines) + 2)
    per_collection = {}
    total_records = 0
    for collection, path in iter_object_files(root):
        record = load_json(path)
        locator = record.get("sourceLocator")
        if not locator:
            continue
        total_records += 1
        per_collection[collection] = per_collection.get(collection, 0) + 1
        for line in range(locator["lineStart"], locator["lineEnd"] + 1):
            if line <= len(lines):
                covered[line] += 1

    uncovered = [
        i
        for i in range(1, len(lines) + 1)
        if lines[i - 1].strip() and not covered[i]
    ]
    report = {
        "sourceFile": SOURCE_FILE,
        "contentFirstLine": 1,
        "contentLines": sum(1 for line in lines if line.strip()),
        "uncoveredLines": uncovered,
        "recordCounts": per_collection,
        "recordsWithLocators": total_records,
    }
    dump_json(root / "objects/sources/source-coverage.json", report)
    if uncovered:
        preview = ", ".join(str(i) for i in uncovered[:20])
        print(f"FAIL: {len(uncovered)} uncovered source lines (first: {preview})")
        sys.exit(1)
    print(
        f"coverage: {report['contentLines']} content lines fully covered "
        f"by {total_records} records"
    )


if __name__ == "__main__":
    main()
