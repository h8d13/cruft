# cruft

> Cruft is a lightweight duplicate code finder that ships with `ruff` and `vulture` basic config.

It is meant to be a boilerplate to use on new Python/PyPy projects or check existing codebases.

---

Why they work well together: 

1. `ruff` as the main coding style + rules enabler + auto fixing, etc
2. `vulture` as a further introspection for any unused code (with some false positives, that can be whitelisted).
3. `cruft` is purely a direct/fuzzy compare which reports many false positives BUT also opportunities to refactor.
