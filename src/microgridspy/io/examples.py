"""Bundled example projects shipped with the package.

These let a user run MicroGridsPy end-to-end immediately after ``pip install``,
without cloning the repository. ``load_example()`` copies an example's inputs
into the active workspace so it can be solved like any other project:

```python
import microgridspy as mgp

mgp.load_example("demo_typical_year")     # -> creates ./projects/demo_typical_year
results = mgp.solve("demo_typical_year").results()
print(results.kpis)
```

The example inputs live under ``microgridspy/examples/<name>/inputs`` inside the
installed package.
"""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

from microgridspy.io.utils import ensure_project_structure, project_paths

# name -> one-line description
EXAMPLES: dict[str, str] = {
    "demo_typical_year": (
        "Off-grid, single-scenario typical-year demo (solar PV + battery + diesel)."
    ),
    "demo_multi_year": (
        "Off-grid, single-scenario 10-year multi-year demo (solar PV + battery + diesel)."
    ),
}


def _examples_root() -> Path:
    """Filesystem path of the bundled examples directory inside the package."""
    return Path(resources.files("microgridspy")) / "examples"


def list_examples() -> list[str]:
    """Return the names of the example projects bundled with the package.

    Returns:
        Sorted list of example names usable with `load_example()`.
    """
    return sorted(EXAMPLES)


def example_description(name: str) -> str:
    """Return the one-line description of a bundled example."""
    if name not in EXAMPLES:
        raise ValueError(f"Unknown example '{name}'. Available: {list_examples()}")
    return EXAMPLES[name]


def load_example(
    name: str = "demo_typical_year",
    dest: str | None = None,
    *,
    overwrite: bool = False,
) -> str:
    """Copy a bundled example project into the active workspace.

    The example's input files are copied into ``<workspace>/projects/<dest>/inputs``
    so the project can then be solved like any other, e.g. with
    `microgridspy.solve()`.

    Args:
        name: the example to load (see `list_examples()`).
        dest: destination project name; defaults to ``name``.
        overwrite: replace the destination project if it already exists.

    Returns:
        The destination project name.

    Raises:
        ValueError: if ``name`` is not a bundled example.
        FileExistsError: if the destination exists and ``overwrite`` is False.
    """
    if name not in EXAMPLES:
        raise ValueError(f"Unknown example '{name}'. Available: {list_examples()}")
    src_inputs = _examples_root() / name / "inputs"
    if not src_inputs.is_dir():
        raise FileNotFoundError(f"Bundled example inputs not found at {src_inputs}.")

    dst_name = dest or name
    dst = project_paths(dst_name)
    if dst.root.exists():
        if not overwrite:
            raise FileExistsError(
                f"Project '{dst_name}' already exists. Pass overwrite=True to replace it."
            )
        shutil.rmtree(dst.root)

    ensure_project_structure(dst_name)
    shutil.copytree(src_inputs, dst.inputs_dir, dirs_exist_ok=True)
    return dst_name
