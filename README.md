# Odoo Access Visualizer 19.0.1.2.0

Read-only Odoo 19 administration module for understanding users, security
groups, implied groups, access control lists, record rules, privileges, models
and menus.

The module belongs in any directory already configured in Odoo's `addons_path`.
It depends only on `base` and `web`.

## What it provides

- Background security snapshots with queued, running, completed and failed states.
- Overview dashboard with access-surface metrics and evidence-backed findings.
- Focused relationship exploration instead of an unreadable full-system graph.
- Access Path view for tracing relationships around a selected object.
- Neighborhood view for exploring one or two relationship hops.
- Permission Matrix view for comparing group-to-model CRUD access without graph noise.
- Snapshot Compare view for reviewing added, removed and changed security objects.
- Effective Read, Write, Create and Delete summaries.
- Record-rule impact and source evidence in the node detail panel.
- Vietnamese translation through the standard Odoo `i18n/vi.po` mechanism.
- Retention of five to ten successful snapshots; five is the default.

## Investigation workflow

1. Open **Settings → Access Visualizer → Security Map**.
2. Start from **Overview**, a question, or a finding.
3. In **Explore map**, choose a layer, module, search term or model permission.
4. Select a display mode: **Access path**, **Neighborhood** or
   **Permission matrix**.
5. Select a node to inspect its effective CRUD access, record-rule impact and
   evidence path.

Focused queries use the selected records as graph seeds and expand up to two
relationship hops. The browser render budget is bounded to 96 nodes and 800
edges per focused response. When a result is larger, the UI reports the
rendered count and the total matching count so the limitation is explicit.

## Findings

- **Implied group overlap:** cross-module groups share a transitive implied group.
- **ACL redundancy and complexity:** duplicate, redundant or unusually dense
  ACL layouts. Odoo ACL permissions are additive.
- **Record-rule interaction:** duplicate rules and potentially important
  global/group rule relationships. Dynamic domains remain warnings unless the
  analyzer can prove a conclusion.

Findings are evidence-backed and separated into deterministic and heuristic
signals. Remediation remains in Odoo's standard security screens; this module
does not modify security source records.

## Scope and limitations

- Odoo 19.0 only.
- Access is restricted to Settings administrators (`base.group_system`).
- Field-level security analysis, inline remediation, exports and real-time
  incremental scanning are not currently included.
- Cytoscape.js 3.34.3 is vendored for focused interactive graphs, with a
  dependency-free SVG fallback for larger or unsupported renders.

## Development and verification

The repository includes Odoo transaction tests covering scanner normalization,
security semantics, snapshot lifecycle, retention, graph expansion, permission
filters and non-admin access. CI also checks Python, JavaScript, XML, YAML and
Odoo module integration tests against PostgreSQL.

Useful local checks from the module directory:

```bash
python -m compileall -q .
node --check static/src/js/access_visualizer_action.js
node --check static/src/js/graph_renderer.js
```

Keep database credentials, dumps, private configuration and workspace-specific
data outside the public module repository.

## License

See [LICENSE](LICENSE) and [NOTICE](NOTICE). Cytoscape.js is distributed with
its corresponding vendor notice.
