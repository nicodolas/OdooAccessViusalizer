# Contributing

## Scope

Odoo Access Visualizer targets Odoo 19.0 and is intentionally read-only. Changes
must preserve the security boundary, snapshot lifecycle and evidence model.

## Local development

1. Put the module directory in an Odoo 19 `addons_path`.
2. Install/update `odoo_access_visualizer` in a disposable database.
3. Run the module tests with `--test-enable`.
4. Run Python, JavaScript and XML syntax checks before opening a pull request.

## Pull requests

- Explain the security semantics affected by the change.
- Add or update a regression test for scanner/analyzer behavior.
- Do not include database dumps, credentials, local configuration or private
  workspace files.
- Keep findings evidence-backed; label heuristic analysis as Warning.

