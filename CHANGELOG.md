# Changelog

All notable changes to this project are documented in this file. The
project follows semantic versioning; corpus counts refer to a clean build.

## [Unreleased]

### Fixed

- Parse Markdown-escaped pipes inside table cells without creating extra
  cells, correcting the HARM table's two affected rows.
- Apply reviewed, line-pinned treatments to two malformed short table header
  delimiters so the HARM and TIER & QUALITY / FORCE headers are no longer
  emitted as data rows.
- Preserve the exact upstream Markdown conversion statement in the README.

### Changed

- Strengthen the fidelity gate to independently reconstruct all 288 source
  sections and compare exact prose, catalog classification, typed grammar
  hits, table structure and widths, locators, relationships, and rights
  metadata.

## [0.2.0] - 2026-08-24

### Added

- Three typed collections extracted from existing rule prose: `vices` (7),
  `plans` (6, each with a typed `detail` field), and `teamwork-maneuvers`
  (4), bringing the corpus to 366 records across 12 collections.
- `partOf` node references from every paragraph- and bullet-grained record
  (actions, crew claims, trauma conditions, vices, plans) to its owning
  rule, making the documented sub-span containment graph-navigable. The
  fidelity gate now verifies each edge targets the owning rule.
- GitHub Pages deployment workflow, NOTICE file describing the MIT /
  CC-BY-3.0 licence boundary, and this changelog.
- Frictionless datapackage resources for the coverage report, extraction
  overrides, JSON Schemas, and sitemap.

### Changed

- Teamwork maneuver sections became typed records, so `rules` counts
  202 instead of 206.

## [0.1.0] - 2026-08-24

### Added

- Initial corpus: 353 records across 9 collections extracted from the
  CC-BY-3.0 Blades in the Dark SRD Markdown conversion, with JSON-LD 1.1
  identity, JSON Schema Draft 2020-12 contracts, line-level provenance,
  aggregate manifest and bundle, search and collection indexes, LLM
  projections, vocabulary, static explorer, and a deterministic build and
  verification pipeline.
