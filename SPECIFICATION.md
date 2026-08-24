# Blades in the Dark SRD System JSON — Technical Specification

Status: v0.2.0. The source-boundary, graph-fidelity, physical-provenance, table, recursive-ingestion, typed-extraction, verification, vocabulary, and documentation requirements are implemented and enforced by `make check`. The architecture adopts [graph20](https://cheeleong.dev/graph20/) (SRD 5.2.1); graph20's occurrence-level semantic-review ledger is not adopted at this corpus size.

## 1. Objective

Turn the local CC-BY-3.0 `Blades-in-the-Dark-SRD.md` into a modular, machine-readable Blades in the Dark SRD corpus with JSON-LD 1.1 identity and relationships, JSON Schema Draft 2020-12 contracts, one file per reusable entity, aggregate artifacts, physical source traceability, and source-faithful prose.

The corpus is reference data. Executable rules engines, character builders, campaign state, and automation inferred from prose remain out of scope.

## 2. Source and legal boundary

`Blades-in-the-Dark-SRD.md` is the sole content source. It is the Markdown conversion of the Blades in the Dark SRD text (bladesinthedark.com) by John Harper (One Seven Design) under CC-BY-3.0, published by Randy Oest (amazingrando) at https://github.com/amazingrando/blades-in-the-dark-srd-content and retained byte for byte from commit `ac2747ffc0806b2be9f14d29b2ace5dca6149bc3` (2022-04-08). The required attribution statement is preserved exactly in the source record, manifest, README, and `llms-full.txt`, alongside a conversion statement crediting the Markdown conversion.

The source file is never repaired in place. Registered normalisations are applied only at extraction time through `objects/sources/extraction-overrides.json`, which records the observed text, the treatment, the rationale, and a reviewed status; the extractor verifies the observed text before honouring an entry. Conversion artefacts (`@TODO` markers, spliced bold spans, `[]()` header placeholders) are registered anomaly detectors with pinned occurrence counts, and `make anomalies` fails on any unreviewed or moved hit.

## 3. Corpus scope

The v0.2.0 clean build contains 366 records:

| Collection | Count | Content |
| --- | ---: | --- |
| sources | 1 | Origin, licence, attribution, conversion provenance, canonical IRI, and SHA-256 digest |
| rules | 202 | Source-faithful general rules and prose sections |
| tables | 15 | Logical source tables with columns, ordered rows, raw source table text, and physical spans |
| actions | 12 | The printed "When you **X**…" paragraphs, play examples, and the attribute read from the rating tables |
| special-abilities | 58 | 42 character and 16 crew abilities; rules text split from `>` designer commentary |
| entanglements | 12 | The post-score entanglement sections |
| downtime-activities | 6 | The six activities listed in the Downtime activities chapter |
| claims | 35 | 29 crew claim-map entries and 6 prison claim sections |
| trauma-conditions | 8 | The trauma condition bullets |
| vices | 7 | The vice bullets in the character-creation "Choose your vice" section |
| plans | 6 | The six plan-type bullets in Planning & engagement, with the typed missing detail |
| teamwork-maneuvers | 4 | The level-3 maneuver sections of the Teamwork chapter |

## 4. Data architecture

| Concern | Decision |
| --- | --- |
| Base IRI | `https://cheeleong.dev/fitd-system-json/` |
| Vocabulary | Fragment IRIs under `https://cheeleong.dev/fitd-system-json/vocab/#` |
| Context | `systems/context.jsonld`, JSON-LD 1.1 |
| Schemas | Draft 2020-12; leaf entities reject unevaluated properties |
| Identity | Stable lowercase-kebab-case canonical `@id` values |
| Relationships | `{ "@id": "..." }` node references only; never bare strings under IRI-coerced predicates |
| Prose | Source wording (Markdown emphasis included) in `rulesText`/`examplesText`/`commentary`; structured fields remain indexes |
| Manifest | Graph-safe collection descriptors with member and schema node references |
| Aggregates | Manifest, JSON-LD bundle, recursive LLM projection, recursive search index, collection index, vocabulary, and sitemap |

## 5. Extraction rules

The source is hierarchical Markdown. Every heading (levels 1–6) starts a section; a section spans its heading through the line before the next heading, with trailing blank lines trimmed. Level-1 headings are chapters, and sections are numbered `<chapter>.<ordinal>` in document order, chapter headings included. Locators carry the chapter title, section number, printed heading, and inclusive line bounds.

Catalog entities are recognised from position and body grammar:

- **actions**: `When you **X**, …` paragraphs in the Actions section, with the following italic example paragraph; each action's attribute is read from the printed EXAMPLE ACTION & ATTRIBUTE RATINGS tables, never hardcoded;
- **special abilities**: sections under "Special abilities" (character) and "Crew special abilities" (crew); the level-2 "Fortitude" heading inside the level-3 run is treated as level 3 through a registered override;
- **entanglements**: the level-3 sections of the Entanglements chapter;
- **downtime activities**: the level-3 sections of the Downtime activities chapter matching the chapter's own six-item list (summary cards such as VICE ROLL remain rules);
- **claims**: the level-3 sections under "Prison claims" (except the CLAIMS: PRISON map card) plus the bold-led paragraphs of "Make a Claim Map for the Crew";
- **trauma conditions**: the bold-led bullets of the Trauma Conditions section;
- **vices**: the bold-led bullets of the character-creation "Choose your vice" section;
- **plans**: the `* Name - … *Detail: …*` bullets in the Planning & engagement chapter body, with the detail captured as a typed field;
- **teamwork maneuvers**: the level-3 sections under the level-2 Teamwork section.

Sections claimed by a catalog grammar become typed records instead of rules. Paragraph- and bullet-grained entities (actions, crew claims, trauma conditions, vices, plans) are typed indexes over rule prose: the owning rule keeps the source-faithful text and the typed records carry sub-spans inside it, plus a `partOf` node reference to the owning rule. In catalog records, `>` blockquote paragraphs are split into `commentary` (designer guidance) with the quote markers removed; all other wording is preserved as printed.

Pipe-table runs become Table records named after their owning section. Tables preserve their physical source span and `rawText`; typed columns normalise the registered `[]()` header placeholder to an empty label. The owning rule's `rulesText` excludes the physical table lines (and `---` horizontal rules) and links each table via `relatedTables`.

## 6. Recursive text projection

`fitdlib.iter_text_fragments` is the shared recursive projection for `llms-full.txt` and full-text search. It covers every prose field and table cell; LLM rendering suppresses redundant contained fragments without dropping their exact text, and search postings carry an excerpt from the matched fragment.

## 7. Verification

`make check` rebuilds every artifact and runs distinct gates:

- `coverage`: interval coverage only; all 1,439 non-blank source lines are inside at least one locator. It does not claim ownership or fidelity.
- `anomalies`: every detector hit must match a reviewed registry disposition with a pinned occurrence count.
- `fidelity`: locator anchoring to printed identity, physical table starts and raw-text equality, sub-span containment in owning rules with matching `partOf` edges, typed catalog counts (12/58/12/6/35/8/7/6/4), and exact rights metadata in the source record, manifest, and `llms-full.txt`.
- `graph`: expands every record, manifest, and bundle; rejects lost compact properties/literals, bare IRI-coerced strings, missing entity types, and undocumented project terms.
- `test`: regression fixtures for the Fortitude heading override, commentary splitting, table spans, downtime summary exclusion, claim types, vice and plan bullets, teamwork maneuver sections, `partOf` targets, attribution survival, and search postings.
- `validate`: identity, bounds, reference resolution, search postings, sitemap XML, and vocabulary targets.
- `schema`: every record, manifest, bundle, search index, collection index, and coverage report against Draft 2020-12 schemas.
- `determinism`: compares two clean builds with each other and with checked-in `objects/`, `llms-full.txt`, `vocab/`, and `sitemap.xml`.

These automated gates establish the repository acceptance criteria; they do not make the project official or expand the source/legal scope.
