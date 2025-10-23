# rjson — YAML/JSON template runner

This repository provides a small template engine and runtime to render YAML or JSON templates into JSON.

Quick start
-----------

1. Install for development:

```powershell
pip install -e .
```

2. Run demo:

```powershell
python -m rjson.cli --demo
```

3. Load addons and render:

```python
from rjson import load_addon, render_template_obj
load_addon('examples/addons/example_addon.py')
print(render_template_obj({'g': "$shout('hi')"}))
```

Docs
----
See the `docs/` folder for CLI and addon usage examples.
