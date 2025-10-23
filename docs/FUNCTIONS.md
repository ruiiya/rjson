# Functions and addons

This project intentionally keeps no built-in helper functions. Add helper functions using addons.

Addon format:

- Provide a `functions` dict mapping name -> callable, for example:

```python
functions = {
    'shout': lambda s: str(s).upper() + '!'
}
```

- Or provide a `register(funcs)` callable that accepts the package `functions` dict and mutates it.
