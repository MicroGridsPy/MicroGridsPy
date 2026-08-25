# Contributing to MicroGridsPy

Thanks for your interest in improving MicroGridsPy! Contributions of all kinds are
welcome — bug reports, feature requests, documentation, and code.

> This is a minimal starting guide and will be expanded. For documentation-specific
> conventions see [`docs/developers/contributing.md`](docs/developers/contributing.md).

## Reporting issues

Please open an issue on the
[issue tracker](https://github.com/MicroGridsPy/MicroGridsPy/issues) and include, where
relevant: what you expected, what happened, a minimal example (or project inputs) that
reproduces the problem, your OS, Python version, and MicroGridsPy version
(`python -c "import microgridspy; print(microgridspy.__version__)"`).

## Development setup

```bash
git clone https://github.com/MicroGridsPy/MicroGridsPy.git
cd MicroGridsPy
pip install -e ".[highs,dev]"
```

## Before opening a pull request

- Keep changes focused and describe the motivation in the PR.
- Run the linters and tests locally:

  ```bash
  ruff check .
  ruff format --check .
  pytest
  ```

- Update [`CHANGELOG.md`](CHANGELOG.md) when behavior changes.
- Add or update tests for new behavior, and update the docs when relevant
  (keep API details in docstrings — the API reference is generated from them).
- If you build the docs, verify they build cleanly (`zensical build`).

## Code style

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
(configured in `pyproject.toml`).

## License

By contributing, you agree that your contributions will be licensed under the project's
[EUPL-1.2 license](LICENSE).
