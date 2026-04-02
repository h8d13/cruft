# cruft

> Cruft is a lightweight duplicate code finder that ships with `ruff` and `vulture` basic config.

It is meant to be a boilerplate to use on new Python & PyPy projects or check existing codebases.

---

Why they work well together: 

1. `ruff` as the main coding style + rules enabler + auto fixing, etc
2. `vulture` as a further introspection for any unused code (with some false positives, that can be whitelisted).
3. `cruft` is a direct/fuzzy compare which reports many false positives BUT also opportunities to refactor.

---

## Install:

All you need is the example `.pre-commit-config.yaml`
```bash
pre-commit install
pre-commit autoupdate
```

And to adapt to your paths and rules `ruff.toml`. 
I've purposely ommited the `[format]` block as I do not like a tool touching my code too much.

## References: 

For more info: 

- https://docs.astral.sh/ruff/formatter/
- https://github.com/h8d13/cruft