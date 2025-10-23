import importlib.util
import os
import types

# Minimal core helper functions intentionally empty — use addons to add helpers.
functions = {}


def _load_module_from_path(path: str) -> types.ModuleType:
    """Load a Python module from a filesystem path and return the module."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_addon(path: str) -> list:
    """Load an addon Python file and merge any `functions` it exposes.

    The addon may expose either:
    - a `functions` dict mapping name -> callable, or
    - a `register` callable that accepts one argument (the existing functions dict)

    Returns a list of function names that were added or updated.
    """
    mod = _load_module_from_path(path)
    added = []
    # If module has a `functions` dict, merge it
    if hasattr(mod, "functions") and isinstance(getattr(mod, "functions"), dict):
        for k, v in getattr(mod, "functions").items():
            functions[k] = v
            added.append(k)
    # If module provides a register(funcs) callable, call it
    if hasattr(mod, "register") and callable(getattr(mod, "register")):
        # The register callable may return names it registered
        result = mod.register(functions)
        if isinstance(result, (list, tuple)):
            added.extend([str(x) for x in result])
    # If module exposes a teardown callable, remember it so users can run cleanup
    if hasattr(mod, "teardown") and callable(getattr(mod, "teardown")):
        _registered_teardowns.append(getattr(mod, "teardown"))
    return added


def load_addons(paths):
    """Load multiple addon paths (list or single path). Returns dict path -> added names."""
    if isinstance(paths, (str, os.PathLike)):
        paths = [paths]
    results = {}
    for p in paths:
        try:
            added = load_addon(p)
            results[p] = added
        except Exception as e:
            results[p] = f"ERROR: {e}"
    return results


def load_addons_from_dir(dirpath: str, pattern: str = "*.py") -> dict:
    """Load all addon files in a directory matching pattern (uses simple filename matching).

    Returns dict file_path -> added names or error message.
    """
    dirpath = os.path.abspath(dirpath)
    if not os.path.isdir(dirpath):
        raise NotADirectoryError(dirpath)
    results = {}
    for name in os.listdir(dirpath):
        if not name.endswith('.py'):
            continue
        path = os.path.join(dirpath, name)
        try:
            results[path] = load_addon(path)
        except Exception as e:
            results[path] = f"ERROR: {e}"
    return results


_registered_teardowns = []


def teardown_addons():
    """Run any registered teardown callables from loaded addons and clear them."""
    errors = []
    while _registered_teardowns:
        fn = _registered_teardowns.pop()
        try:
            fn()
        except Exception as e:
            errors.append(str(e))
    return errors
