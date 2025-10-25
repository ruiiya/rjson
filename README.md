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

# rjson — JSON/YAML template runner (short)

Small template runner that renders JSON/YAML templates containing inline expressions.

Install (development):

```powershell
pip install -e .
```

Quick Python example:

```python
from rjson import load_addon
from rjson.template_runtime import TemplateRuntime

load_addon('examples/addons/generate_helpers.py')
rt = TemplateRuntime(context={'score': 75})
print(rt.render({'result': '$score >= 50 ? "pass" : "fail"'}))
```

See the `docs/` directory for detailed English documentation (CLI was removed from this project).
