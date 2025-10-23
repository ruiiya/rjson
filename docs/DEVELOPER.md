# Developer notes

- Addons are loaded via `rjson.load_addon(path)` or `rjson.load_addons_from_dir(dir)`.
- Templates may be YAML or JSON; use `rjson.load_and_render_file(path)` or the CLI `--file` option.
- To test: `python -m pytest`