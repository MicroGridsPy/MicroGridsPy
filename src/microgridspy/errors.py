"""The exception MicroGridsPy raises for invalid inputs.

Every layer — project scaffolding, input parsing, model building and results
export — raises :class:`InputValidationError` when the inputs it was given do not
make sense. One class means a single ``except`` clause catches all of them::

    import microgridspy as mgp

    try:
        model = mgp.solve("my_site")
    except mgp.InputValidationError as exc:
        print(f"bad inputs: {exc}")
"""

from __future__ import annotations


class InputValidationError(RuntimeError):
    """Raised when a project's inputs are missing, malformed or inconsistent."""
