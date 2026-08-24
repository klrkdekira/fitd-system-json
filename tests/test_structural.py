"""Structural regression fixtures for the Blades in the Dark SRD corpus."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fitdlib import (  # noqa: E402
    ATTRIBUTION_STATEMENT,
    BUNDLE_NAME,
    COLLECTIONS,
    CONVERSION_STATEMENT,
    MANIFEST_NAME,
    SOURCE_FILE,
    VERSION,
    iter_object_files,
    load_json,
    projected_text,
)


def record(collection: str, slug: str) -> dict:
    return load_json(ROOT / "objects" / collection / f"{slug}.jsonld")


class TestActions(unittest.TestCase):
    def test_twelve_actions_with_table_backed_attributes(self):
        actions = {
            path.stem: load_json(path)
            for c, path in iter_object_files(ROOT)
            if c == "actions"
        }
        self.assertEqual(len(actions), 12)
        self.assertEqual(actions["hunt"]["attribute"], "Insight")
        self.assertEqual(actions["wreck"]["attribute"], "Prowess")
        self.assertEqual(actions["sway"]["attribute"], "Resolve")

    def test_action_keeps_printed_wording_and_examples(self):
        attune = record("actions", "attune")
        self.assertEqual(
            attune["rulesText"],
            "When you **Attune**, you open your mind to arcane power.",
        )
        self.assertIn("communicate with a ghost", attune["examplesText"])


class TestSpecialAbilities(unittest.TestCase):
    def test_fortitude_heading_override(self):
        # Fortitude is printed at heading level 2 inside the level-3 ability
        # run; the registered override keeps it a character ability.
        fortitude = record("special-abilities", "fortitude")
        self.assertEqual(fortitude["abilityScope"], "character")
        self.assertIn("special armor", fortitude["rulesText"])

    def test_crew_ability_scope_and_commentary_split(self):
        deadly = record("special-abilities", "deadly")
        self.assertEqual(deadly["abilityScope"], "crew")
        battleborn = record("special-abilities", "battleborn")
        self.assertNotIn(">", battleborn["rulesText"])
        self.assertIn("tick the special armor box", battleborn["commentary"])


class TestCatalogRecords(unittest.TestCase):
    def test_entanglement_fixture(self):
        arrest = record("entanglements", "arrest")
        self.assertIn("Inspector", arrest["rulesText"])
        self.assertIn("truncheon", arrest["commentary"])

    def test_downtime_activities_exclude_summary_cards(self):
        slugs = {
            path.stem
            for c, path in iter_object_files(ROOT)
            if c == "downtime-activities"
        }
        self.assertEqual(
            slugs,
            {
                "acquire-asset",
                "long-term-project",
                "recover",
                "reduce-heat",
                "train",
                "indulge-vice",
            },
        )

    def test_claim_types(self):
        self.assertEqual(record("claims", "turf")["claimType"], "crew")
        self.assertEqual(record("claims", "smuggling")["claimType"], "prison")

    def test_trauma_condition_bullet(self):
        cold = record("trauma-conditions", "cold")
        self.assertTrue(cold["rulesText"].startswith("**Cold**:"))

    def test_vice_bullets(self):
        slugs = {
            path.stem for c, path in iter_object_files(ROOT) if c == "vices"
        }
        self.assertEqual(
            slugs,
            {"faith", "gambling", "luxury", "obligation", "pleasure",
             "stupor", "weird"},
        )
        faith = record("vices", "faith")
        self.assertTrue(faith["rulesText"].startswith("**Faith**:"))

    def test_plan_detail_field(self):
        assault = record("plans", "assault")
        self.assertEqual(assault["detail"], "The point of attack.")
        slugs = {
            path.stem for c, path in iter_object_files(ROOT) if c == "plans"
        }
        self.assertEqual(
            slugs,
            {"assault", "deception", "stealth", "occult", "social",
             "transport"},
        )

    def test_teamwork_maneuver_sections(self):
        slugs = {
            path.stem
            for c, path in iter_object_files(ROOT)
            if c == "teamwork-maneuvers"
        }
        self.assertEqual(
            slugs, {"assist", "lead-a-group-action", "protect", "set-up"}
        )
        assist = record("teamwork-maneuvers", "assist")
        self.assertIn("Take 1 stress", assist["rulesText"])

    def test_sub_span_records_link_their_owning_rule(self):
        expectations = {
            ("actions", "wreck"): "3-10-actions",
            ("claims", "turf"): "20-6-make-a-claim-map-for-the-crew",
            ("trauma-conditions", "cold"): "4-5-trauma-conditions",
            ("vices", "faith"): "17-9-choose-your-vice",
            ("plans", "assault"): "22-1-planning-engagement",
        }
        for (collection, slug), rule_slug in expectations.items():
            self.assertEqual(
                record(collection, slug)["partOf"]["@id"],
                f"https://cheeleong.dev/fitd-system-json/objects/rules/{rule_slug}",
            )


class TestTablesAndRules(unittest.TestCase):
    def test_table_raw_text_matches_source_span(self):
        lines = (ROOT / SOURCE_FILE).read_text(encoding="utf-8").splitlines()
        for collection, path in iter_object_files(ROOT):
            if collection != "tables":
                continue
            table = load_json(path)
            locator = table["sourceLocator"]
            span = "\n".join(lines[locator["lineStart"] - 1 : locator["lineEnd"]])
            self.assertEqual(table["rawText"], span, path.stem)

    def test_rule_prose_excludes_table_lines_and_links_them(self):
        entanglements = record("rules", "27-1-entanglements")
        self.assertNotIn("| RESULT |", entanglements["rulesText"])
        self.assertEqual(len(entanglements["relatedTables"]), 1)

    def test_normalized_header_placeholder(self):
        prison = record("tables", "26-5-claims-prison")
        self.assertEqual(prison["columns"][0], "")
        self.assertIn("[]()", prison["rawText"])

    def test_escaped_pipes_do_not_split_harm_cells(self):
        harm = record("tables", "9-7-harm")
        self.assertEqual(harm["columns"], ["", "", ""])
        self.assertEqual(len(harm["rows"]), 3)
        self.assertTrue(harm["rows"][1]["cells"][1]["value"].endswith(r"\|"))
        for row in harm["rows"]:
            self.assertEqual(len(row["cells"]), len(harm["columns"]))

    def test_short_separator_override_keeps_magnitude_header(self):
        table = record("tables", "29-4-tier-quality-force")
        self.assertEqual(table["columns"], [str(value) for value in range(7)])
        self.assertEqual(len(table["rows"]), 2)

    def test_every_table_row_matches_its_column_width(self):
        for collection, path in iter_object_files(ROOT):
            if collection != "tables":
                continue
            table = load_json(path)
            for row in table["rows"]:
                self.assertEqual(
                    len(row["cells"]), len(table["columns"]), path.stem
                )


class TestCorpusInvariants(unittest.TestCase):
    def test_unique_slugs_within_collections(self):
        for collection in COLLECTIONS:
            directory = ROOT / "objects" / collection
            slugs = [p.stem for p in directory.glob("*.jsonld")]
            self.assertEqual(len(slugs), len(set(slugs)), collection)

    def test_attribution_survives_all_projections(self):
        source = record("sources", "blades-in-the-dark-srd")
        self.assertEqual(source["attributionStatement"], ATTRIBUTION_STATEMENT)
        self.assertEqual(source["conversionStatement"], CONVERSION_STATEMENT)
        self.assertIn(
            ATTRIBUTION_STATEMENT,
            (ROOT / "llms-full.txt").read_text(encoding="utf-8"),
        )
        self.assertIn(
            CONVERSION_STATEMENT,
            (ROOT / "README.md").read_text(encoding="utf-8"),
        )
        self.assertIn(ATTRIBUTION_STATEMENT, projected_text(source))

    def test_search_index_covers_nested_prose(self):
        index = load_json(ROOT / "objects/search-index.json")
        self.assertIn("flashback", index["tokens"])
        self.assertIn("entanglement", index["tokens"])

    def test_version_consistency(self):
        manifest = load_json(ROOT / "objects" / MANIFEST_NAME)
        bundle = load_json(ROOT / "objects" / BUNDLE_NAME)
        self.assertEqual(manifest["version"], VERSION)
        self.assertEqual(bundle["version"], VERSION)
        self.assertEqual(VERSION, "0.2.0")


if __name__ == "__main__":
    unittest.main()
