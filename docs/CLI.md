# CLI

Usage:

```powershell
python -m rjson.cli [--demo] [--file PATH] [--addon PATH] [--addon-dir DIR] [--out PATH]
```

Options
- `--demo` : run built-in demo
- `--file PATH` : render a YAML or JSON template file
- `--addon PATH` : load an addon Python file (can be repeated)
- `--addon-dir DIR` : load all `.py` addon files from a directory
- `--out PATH` : write output JSON to file

Examples

```powershell
python -m rjson.cli --addon-dir examples/addons --file template.yml
```