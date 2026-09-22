# Changelog

## 19.0.1.2.0 — Snapshot comparison

- Added read-only snapshot comparison for nodes, relationships and findings.
- Added added/removed/changed object summaries in the Compare view.
- Removed the repository worktree used for earlier localization development.

## 19.0.1.1.0 — Investigation hardening

- Added model permission filters for read, write, create and delete access.
- Added two-hop neighborhood expansion and selected-path highlighting.
- Added effective CRUD and record-rule evidence in node details.
- Replaced deprecated Odoo 19 `read_group` usage with `_read_group`.
- Added concurrency protection for queued scans and stronger non-admin tests.
- Added Odoo integration tests to the GitHub Actions quality workflow.

## 19.0.1.0.0 — Initial MVP

- Added read-only background security snapshots.
- Added graph nodes for users, groups, implied groups, privileges, models,
  ACLs, record rules and menus.
- Added deterministic/heuristic findings for implied groups, ACLs and record
  rules.
- Added admin-only OWL client action and bounded SVG graph rendering.
- Added snapshot lifecycle, retention and initial test coverage.
