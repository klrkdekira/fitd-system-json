# Blades in the Dark SRD System JSON

[![CI](https://github.com/klrkdekira/fitd-system-json/actions/workflows/ci.yml/badge.svg)](https://github.com/klrkdekira/fitd-system-json/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/klrkdekira/fitd-system-json)
[![JSON-LD 1.1](https://img.shields.io/badge/JSON--LD-1.1-blue.svg)](https://www.w3.org/TR/json-ld11/)
[![Content License: CC BY 3.0](https://img.shields.io/badge/Content_License-CC_BY_3.0-lightgrey.svg)](https://creativecommons.org/licenses/by/3.0/)
[![Code License: MIT](https://img.shields.io/badge/Code_License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A source-faithful, machine-readable edition of the **Blades in the Dark SRD** (Forged in the Dark rules). The repository turns the CC-BY-3.0 source Markdown into 366 modular records across 12 collections, with:

- JSON-LD 1.1 identity and graph relationships;
- JSON Schema Draft 2020-12 contracts;
- the original SRD prose alongside typed fields for discovery and filtering; and
- line-level provenance back to the authoritative source.

This is a reference corpus, not a rules engine or character builder. It adopts the architecture of [graph20](https://cheeleong.dev/graph20/), the SRD 5.2.1 corpus, which in turn follows [wwn-system-json](https://cheeleong.dev/wwn-system-json/).

[Explore the corpus](https://cheeleong.dev/fitd-system-json/) · [Read the vocabulary](https://cheeleong.dev/fitd-system-json/vocab/) · [Technical specification](SPECIFICATION.md) · [LLM guide](llms.txt)

## Start here

The repository is published as static files, so consumers do not need an API key, database, or runtime.

| I want to… | Start with |
| --- | --- |
| Browse and search the SRD | [Web explorer](https://cheeleong.dev/fitd-system-json/) |
| Fetch one record | [`objects/<collection>/<slug>.jsonld`](objects/actions/wreck.jsonld) |
| Load the complete graph | [`objects/fitd-system-data.bundle.jsonld`](https://cheeleong.dev/fitd-system-json/objects/fitd-system-data.bundle.jsonld) |
| Discover collections and record IDs | [`objects/fitd-system-data.jsonld`](https://cheeleong.dev/fitd-system-json/objects/fitd-system-data.jsonld) |
| Build a search or browse UI | [`objects/search-index.json`](https://cheeleong.dev/fitd-system-json/objects/search-index.json) and [`objects/collection-index.json`](https://cheeleong.dev/fitd-system-json/objects/collection-index.json) |
| Give the corpus to an LLM | [`llms-full.txt`](https://cheeleong.dev/fitd-system-json/llms-full.txt) |
| Resolve classes and properties | [`vocab/terms.json`](https://cheeleong.dev/fitd-system-json/vocab/terms.json) |
| Validate an integration | [`systems/`](systems/) |

For example, fetch a single action or the complete bundle:

```bash
curl -fsSL https://cheeleong.dev/fitd-system-json/objects/actions/wreck.jsonld
curl -fsSL https://cheeleong.dev/fitd-system-json/objects/fitd-system-data.bundle.jsonld -o fitd.jsonld
```

Record files use the path `objects/<collection>/<slug>.jsonld`. Inside a record, the canonical `@id` omits the file extension:

```json
{
  "@context": "https://cheeleong.dev/fitd-system-json/systems/context.jsonld",
  "@id": "https://cheeleong.dev/fitd-system-json/objects/actions/wreck",
  "@type": "Action",
  "name": "Wreck",
  "source": {
    "@id": "https://cheeleong.dev/fitd-system-json/objects/sources/blades-in-the-dark-srd"
  },
  "sourceLocator": {
    "chapter": "Actions & Attributes",
    "section": "3.10",
    "heading": "Actions",
    "lineStart": 204,
    "lineEnd": 206
  },
  "attribute": "Prowess",
  "rulesText": "When you **Wreck**, you unleash savage force."
}
```

The example is abbreviated. The full record also retains the printed play examples.

## Published artifacts

| Artifact | Purpose |
| --- | --- |
| [`objects/fitd-system-data.jsonld`](https://cheeleong.dev/fitd-system-json/objects/fitd-system-data.jsonld) | Manifest containing corpus metadata, source and corpus digests, collection descriptors, member links, and schema links. |
| [`objects/fitd-system-data.bundle.jsonld`](https://cheeleong.dev/fitd-system-json/objects/fitd-system-data.bundle.jsonld) | All 366 records in one JSON-LD `@graph`. |
| [`objects/search-index.json`](https://cheeleong.dev/fitd-system-json/objects/search-index.json) | Static inverted index over all records and nested text fragments. |
| [`objects/collection-index.json`](https://cheeleong.dev/fitd-system-json/objects/collection-index.json) | Compact display and filter metadata such as action attribute, ability scope, and claim type. |
| [`systems/context.jsonld`](https://cheeleong.dev/fitd-system-json/systems/context.jsonld) | Shared JSON-LD context, including IRI coercion rules. |
| [`systems/*.schema.json`](systems/) | Draft 2020-12 schemas for records, aggregates, and verification reports. |
| [`vocab/terms.json`](https://cheeleong.dev/fitd-system-json/vocab/terms.json) | Definitions for the classes and properties in the project vocabulary. |
| [`llms.txt`](https://cheeleong.dev/fitd-system-json/llms.txt) / [`llms-full.txt`](https://cheeleong.dev/fitd-system-json/llms-full.txt) | LLM-oriented entry point and full recursive text projection. |
| [`objects/sources/source-coverage.json`](objects/sources/source-coverage.json) | Machine-readable line-coverage report. |
| [`datapackage.json`](datapackage.json) | Frictionless Data Package metadata and resource listing. |

## Corpus inventory

The v0.2.0 build contains:

| Collection | Records | What is represented |
| --- | ---: | --- |
| `sources` | 1 | Source identity, licence, attribution, conversion provenance, and SHA-256 digest |
| `rules` | 202 | General rules, chapters, and reference prose |
| `tables` | 15 | Logical tables with ordered rows, raw Markdown, and physical spans |
| `actions` | 12 | The twelve actions with their attribute (from the printed rating tables) and play examples |
| `special-abilities` | 58 | 42 character and 16 crew special abilities, rules text split from designer commentary |
| `entanglements` | 12 | Post-score entanglements with resolution text and example commentary |
| `downtime-activities` | 6 | The six listed downtime activities |
| `claims` | 35 | 29 crew claim-map claims and 6 prison claims |
| `trauma-conditions` | 8 | The permanent trauma conditions |
| `vices` | 7 | The seven vices from the character-creation list |
| `plans` | 6 | The six score plan types, each with its typed missing detail |
| `teamwork-maneuvers` | 4 | Assist, lead a group action, protect, and set up |
| **Total** | **366** | **1,439 non-blank source lines, 100% covered** |

## Data model and guarantees

The project is designed for source-backed reference and retrieval workloads:

- **Stable identity.** Every entity has a lowercase-kebab-case canonical `@id` under `https://cheeleong.dev/fitd-system-json/` and an `@type` defined by the shared context.
- **Graph-safe links.** Semantic relationships use `{ "@id": "…" }` node references. `$ref` is reserved for JSON Schema composition.
- **Source-faithful prose.** `rulesText`, `examplesText`, and `commentary` preserve source wording, Markdown emphasis included. Typed sibling fields are indexes, not replacements for the prose.
- **Physical provenance.** `sourceLocator` identifies the source chapter, section, heading, and inclusive line range. Paragraph- and bullet-grained records (actions, crew claims, trauma conditions, vices, plans) carry sub-spans inside their owning rule and link it with a `partOf` node reference.
- **No invented values.** Extraction does not fill gaps in the source; conversion artefacts are retained and registered rather than silently repaired.
- **Reviewed normalisation.** Extraction-time normalisations are recorded in [`objects/sources/extraction-overrides.json`](objects/sources/extraction-overrides.json) with observed text, disposition, and rationale, and `make anomalies` rejects unreviewed detector hits.
- **Deterministic output.** Clean builds contain no timestamps or random ordering and must reproduce the checked-in artifacts byte for byte.

The build reports 100% interval coverage of the 1,439 non-blank source lines. Coverage means every line falls within at least one record locator; the separate fidelity, graph, schema, and anomaly gates test stronger claims.

See [SPECIFICATION.md](SPECIFICATION.md) for the source boundary, extraction grammar, architecture, and acceptance criteria.

## Development

### Prerequisites

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

Install the locked development environment and run the full verification pipeline:

```bash
make install
make check
```

`make check` first verifies that checked-in generated artifacts are reproducible, then rebuilds the corpus and runs every validation gate. CI also requires the working tree to remain clean after the pipeline.

For the common extraction path:

```bash
make extract manifest bundle llms-full search-index
make test validate schema
make determinism
```

Generated files under `objects/` must not be edited by hand, except for `objects/sources/extraction-overrides.json`. Change the extraction or build scripts, then regenerate the affected artifacts.

### Make targets

| Target | Result |
| --- | --- |
| `install` | Synchronise the locked development dependencies with uv. |
| `extract` | Re-extract modular records from `Blades-in-the-Dark-SRD.md`. |
| `manifest` / `bundle` | Rebuild the aggregate manifest and single-file graph. |
| `llms-full` | Regenerate the recursive LLM text projection. |
| `search-index` / `collection-index` | Rebuild full-text search postings and compact browse metadata. |
| `coverage` | Check interval coverage of non-blank source lines. |
| `vocab` / `sitemap` | Rebuild vocabulary documentation and the published sitemap. |
| `anomalies` | Reject unreviewed source-conversion anomaly candidates. |
| `fidelity` | Check locator ownership, table shape, and typed/source fidelity. |
| `graph` | Expand JSON-LD and reject data loss or invalid IRI values. |
| `test` | Run the structural regression suite. |
| `validate` | Check identities, bounds, references, indexes, sitemap, and vocabulary targets. |
| `schema` | Validate records and auxiliary artifacts against their JSON Schemas. |
| `determinism` | Compare clean builds with each other and with checked-in output. |
| `check` | Run the complete build and verification gate. |

Run `make help` for the short command reference. Every Python target executes through `uv run` using the locked environment.

## Repository layout

```text
fitd-system-json/
├── Blades-in-the-Dark-SRD.md   # Authoritative in-scope CC-BY-3.0 source
├── objects/                    # Generated records, manifest, bundle, and indexes
│   └── sources/                # Source metadata and extraction/coverage reports
├── systems/                    # JSON-LD context and JSON Schema contracts
├── vocab/                      # Vocabulary browser and machine-readable terms
├── scripts/                    # Deterministic extraction, build, and validation tools
├── tests/                      # Structural regression tests
├── index.html                  # Dependency-free static web explorer
├── llms.txt                    # LLM-oriented corpus guide
├── llms-full.txt               # Full recursive text projection
├── SPECIFICATION.md            # Source of truth for architecture and acceptance
└── Makefile                    # Build and verification entry points
```

## Scope

`Blades-in-the-Dark-SRD.md` is the sole content source: the Markdown conversion of the SRD text at [bladesinthedark.com](https://bladesinthedark.com/) published by Randy Oest (amazingrando) in [blades-in-the-dark-srd-content](https://github.com/amazingrando/blades-in-the-dark-srd-content) (commit `ac2747ff`, 2022-04-08). Material from the full rulebook, wikis, or other Forged in the Dark games is not mixed into the corpus. Executable rules interpretation, campaign state, character building, and automation inferred from prose are intentionally out of scope.

## Licence and attribution

Repository-authored code, schemas, and documentation are available under the [MIT License](LICENSE). SRD content is used under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) with the required attribution:

> This work is based on Blades in the Dark (found at http://www.bladesinthedark.com/), product of One Seven Design, developed and authored by John Harper, and licensed for our use under the Creative Commons Attribution 3.0 Unported license (http://creativecommons.org/licenses/by/3.0/).

The Markdown conversion of the SRD text is by Randy Oest ([amazingrando](https://github.com/amazingrando/blades-in-the-dark-srd-content)). Project citation metadata is available in [`CITATION.cff`](CITATION.cff).

This is an independent, unofficial reference project and is not affiliated with, sponsored by, or endorsed by One Seven Design or John Harper.
