# Writing addons for rjson

rjson supports adding helper functions via addon Python files. There are two supported patterns:

1) Export a `functions` dict

```python
# my_addon.py
functions = {
    'shout': lambda s: str(s).upper() + '!',
}
```

2) Export a `register(funcs)` callable

```python
# my_addon2.py
def register(funcs):
    def shout(s):
        return str(s).upper() + '!'
    funcs['shout'] = shout
    return ['shout']
```

Notes
- Addons are loaded by path using `rjson.load_addon(path)` or via CLI with `--addon path` or `--addon-dir dir`.
- Addons execute in the local process — only load trusted code.

Unit test example

```python
from rjson import load_addon, render_template_obj

def test_addon_loads():
    load_addon('examples/addons/example_addon.py')
    out = render_template_obj({'g': "$shout('hi')"})
    assert out['g'] == 'HI!'
```


Best practices
--------------

- Keep addon functions small and pure (no side-effects). Helpers should accept Python values and return JSON-serializable results.
- Prefer explicit names and avoid shadowing built-in names (e.g. avoid naming a helper `len`).
- Validate inputs early and raise clear exceptions for invalid types.
- Keep state out of helpers. If you need state (for caches, random seeds, or external clients), provide a `register(funcs)` that captures the state in closures.
- Document each helper with a short docstring and example usage in the addon file.
- Add unit tests alongside addons (see `test_examples_addon.py`) that load the addon and exercise its functions via template rendering.

Security
--------

Addons execute arbitrary Python in-process. Only load addons you trust. If you need to run untrusted code, run it in a sandboxed process or separate service.

Examples of slightly more complex addons
--------------------------------------
- `repeat(s, n)` — repeat string `s` `n` times and return a string.
- `sum_list(lst)` — sum numeric values in a list.
- `upper_join(sep, items)` — uppercase all items and join with `sep`.

Use these in templates by loading the addon and rendering a template that references variables or literal lists.

Stateful addons and teardown
---------------------------

You can expose a `teardown()` callable in your addon or return a teardown function from `register` by storing it on the module. The runtime exposes `rjson.teardown_addons()` which runs registered teardown callables for loaded addons. Use this to clear caches or close connections.

Example (pattern):

```python
# stateful_addon.py
def register(funcs):
    cache = {}
    def cached_calc(key, n=1):
        if key in cache:
            return cache[key]
        val = sum(range(int(n)))
        cache[key] = val
        return val
    def teardown():
        cache.clear()
    funcs['cached_calc'] = cached_calc
    # expose the teardown at module level
    global _teardown
    _teardown = teardown
    return ['cached_calc']

def teardown():
    try:
        _teardown()
    except Exception:
        pass
```

When writing tests, call `rjson.teardown_addons()` after running addon tests to ensure cleanup.
