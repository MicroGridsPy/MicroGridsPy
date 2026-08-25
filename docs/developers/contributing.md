# Contributing

Documentation is developed **together with** the Python package. Keep prose in Markdown and
API details in docstrings, so the two never drift.

## Documentation rules

- Keep user-facing explanations in Markdown under `docs/`.
- Keep API details in **Python docstrings** and expose them through mkdocstrings — do not
  duplicate signatures or parameters by hand.
- Update the [Methodology](../methodology/overview.md) whenever the implemented formulation
  changes; the code is authoritative when it disagrees with the formulation document.
- Update the [Internal Data Contract](../data-reference/data-contract.md) *first* when the
  canonical dataset changes, then the loaders and formulation aliases.
- Prefer reproducible examples.
- Test the documentation build locally before opening a pull request.

## Building the docs locally

```bash
pip install -e ".[docs]"
zensical serve      # live preview at http://127.0.0.1:8000
zensical build      # static build into ./site
```

mkdocstrings reads the package statically from `src/` (via Griffe), so the package does not
need to be importable for the docs to build. Read the Docs runs the same `zensical build`
(see `.readthedocs.yaml`).

## Code style and tests

The project uses **Ruff** for linting/formatting and **pytest** for tests (install with the
`[dev]` extra):

```bash
pip install -e ".[highs,dev]"
ruff check .
pytest
```

## Pull requests

A documentation pull request should build cleanly before it is merged. Read the Docs can
then build the PR version and provide a preview for visual review. Keep changes focused,
update the changelog when behavior changes, and cross-link related methodology and API pages.
