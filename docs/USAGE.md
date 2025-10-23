# Usage

Render YAML:

```powershell
python -m rjson.cli --file template.yml
```

Render JSON:

```powershell
python -m rjson.cli --file template.json
```

Load addons:

```powershell
python -m rjson.cli --addon examples/addons/example_addon.py --file template.yml
```